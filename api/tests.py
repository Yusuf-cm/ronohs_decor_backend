from decimal import Decimal
from unittest.mock import patch
from types import SimpleNamespace
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from .models import Product, Order


class CustomerJourneyTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('customer', password='Test-only-good-password-42')
        self.product = Product.all_products.create(name='Test chair', price=Decimal('1000'), stock=5)
        self.payload = {'items': [{'id': self.product.id, 'quantity': 2}], 'customer_details': {
            'firstName': 'Test', 'lastName': 'Customer', 'email': 'test@example.invalid',
            'phone': '0700000000', 'address_line_1': 'Test address', 'city': 'Nairobi', 'county': 'Nairobi'}}

    def test_login_and_refresh(self):
        response = self.client.post('/api/auth/token/', {'username': 'customer', 'password': 'Test-only-good-password-42'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post('/api/auth/token/refresh/', {'refresh': response.data['refresh']}).status_code, 200)

    def test_checkout_requires_login(self):
        self.assertEqual(self.client.post('/api/create-payment-intent/', self.payload, format='json').status_code, 401)

    def test_invalid_quantities_are_rejected_without_orders(self):
        self.client.force_authenticate(self.user)
        for value in [0, -1, 'bad', 1.5, None, 1001]:
            self.payload['items'][0]['quantity'] = value
            self.assertEqual(self.client.post('/api/create-payment-intent/', self.payload, format='json').status_code, 400, value)
        self.assertEqual(Order.objects.count(), 0)

    def test_duplicate_products_rejected(self):
        self.client.force_authenticate(self.user)
        self.payload['items'] *= 2
        self.assertEqual(self.client.post('/api/create-payment-intent/', self.payload, format='json').status_code, 400)

    @patch('api.views.stripe.PaymentIntent.create', return_value=SimpleNamespace(client_secret='test-only'))
    def test_checkout_uses_database_prices(self, payment):
        self.client.force_authenticate(self.user)
        self.payload['items'][0]['price'] = 1
        response = self.client.post('/api/create-payment-intent/', self.payload, format='json')
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=response.data['orderId'])
        self.assertEqual(order.subtotal, Decimal('2000'))
        self.assertEqual(order.grand_total, Decimal('2620'))
        self.assertEqual(payment.call_args.kwargs['amount'], 262000)
        self.assertFalse(order.paid)

    def test_other_customer_cannot_read_order(self):
        other = User.objects.create_user('other')
        order = Order.objects.create(user=other, first_name='Other', last_name='Customer', email='other@example.invalid', phone='0')
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(f'/api/orders/{order.pk}/').status_code, 404)

    def test_registration_with_optional_names(self):
        response = self.client.post('/api/auth/register/', {'username': 'new-user', 'email': 'new@example.invalid', 'password': 'New-test-password-76'}, format='json')
        self.assertEqual(response.status_code, 201)

    def test_weak_password_returns_validation_error(self):
        response = self.client.post('/api/auth/register/', {'username': 'weak-user', 'email': 'weak@example.invalid', 'password': '123'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username='weak-user').exists())

    def test_email_required_without_server_error(self):
        response = self.client.post('/api/auth/register/', {'username': 'missing-email', 'password': 'Good-test-password-42'}, format='json')
        self.assertEqual(response.status_code, 400)

    @patch('api.views.stripe.Webhook.construct_event')
    def test_webhook_retry_only_deducts_stock_once(self, construct):
        from django.test import override_settings
        from .models import OrderItem
        order = Order.objects.create(user=self.user, first_name='Test', last_name='Customer', email='test@example.invalid', phone='0', grand_total=Decimal('1000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=self.product.price)
        construct.return_value = {'type': 'payment_intent.succeeded', 'data': {'object': {'metadata': {'order_id': str(order.id)}, 'currency': 'kes', 'amount_received': 100000}}}
        with override_settings(STRIPE_WEBHOOK_SECRET='test-only'):
            for _ in range(2):
                self.assertEqual(self.client.post('/api/stripe-webhook/', {}, format='json').status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)

    @patch('api.views.stripe.Webhook.construct_event')
    def test_wrong_payment_amount_does_not_mark_order_paid(self, construct):
        from django.test import override_settings
        order = Order.objects.create(user=self.user, first_name='Test', last_name='Customer', email='test@example.invalid', phone='0', grand_total=Decimal('1000'))
        construct.return_value = {'type': 'payment_intent.succeeded', 'data': {'object': {'metadata': {'order_id': str(order.id)}, 'currency': 'kes', 'amount_received': 100}}}
        with override_settings(STRIPE_WEBHOOK_SECRET='test-only'):
            self.assertEqual(self.client.post('/api/stripe-webhook/', {}, format='json').status_code, 400)
        order.refresh_from_db()
        self.assertFalse(order.paid)
