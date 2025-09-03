# api/views.py

import stripe
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Case, When, Value, Count
from django.db.models.functions import TruncDate, Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, status, permissions, filters, viewsets
from django_filters import rest_framework as django_filters

from .models import (
    Product, Category, Project, ContactInquiry, Order, OrderItem, 
    BlogPost, BlogCategory, Author, Coupon, ProjectCategory,
    Attribute, AttributeValue, Wishlist
)
from .serializers import (
    ProductSerializer, CategorySerializer, ProjectSerializer, 
    ContactInquirySerializer, OrderSerializer, BlogPostSerializer, 
    BlogCategorySerializer, AuthorSerializer, ProjectCategorySerializer,
    AttributeSerializer, WishlistSerializer
)
from users.serializers import AdminUserListSerializer
from .permissions import IsSuperUser

# Constants for business logic
SHIPPING_COST_THRESHOLD = Decimal('5000.00')
SHIPPING_COST_STANDARD = Decimal('300.00')
TAX_RATE = Decimal('0.16')  # 16% VAT

class ValidateCouponView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        code = request.data.get('code', '').strip().upper()
        if not code:
            return Response({'error': 'Coupon code is required.'}, status=status.HTTP_400_BAD_REQUEST)

        coupon = Coupon.objects.get_active_coupon(code)

        if coupon:
            return Response({
                'code': coupon.code,
                'discount_percent': coupon.discount_percent
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid or expired coupon code.'}, status=status.HTTP_404_NOT_FOUND)

class WishlistDetailView(generics.RetrieveAPIView):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        wishlist, created = Wishlist.objects.get_or_create(user=self.request.user)
        return wishlist
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class WishlistToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        
        # Toggle logic
        if product in wishlist.products.all():
            wishlist.products.remove(product)
            action = 'removed'
        else:
            wishlist.products.add(product)
            action = 'added'
            
        # Get updated list of product IDs
        updated_wishlist_ids = list(wishlist.products.values_list('id', flat=True))
        
        return Response({
            "action": action, 
            "wishlist": updated_wishlist_ids
        }, status=status.HTTP_200_OK)

class ProductFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='iexact')
    
    class Meta:
        model = Product
        fields = ['category']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for attribute in Attribute.objects.all():
            self.filters[f'filter_{attribute.slug}'] = django_filters.ModelMultipleChoiceFilter(
                field_name='attributes__value',
                to_field_name='value',
                queryset=AttributeValue.objects.filter(attribute=attribute),
                conjoined=False,
            )

class ProductListAPIView(generics.ListAPIView):
    queryset = Product.all_products.all().order_by('-is_featured', '-created_at') 
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    filter_backends = [
        django_filters.DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    search_fields = ['name', 'description', 'category__name', 'sku']
    ordering_fields = ['price', 'created_at']
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class FeaturedProductListAPIView(generics.ListAPIView):
    queryset = Product.objects.filter(is_featured=True)
    serializer_class = ProductSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class ProductDetailAPIView(generics.RetrieveAPIView):
    queryset = Product.all_products.all() 
    serializer_class = ProductSerializer
    lookup_field = 'pk'
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class ProductAttributeListView(generics.ListAPIView):
    queryset = Attribute.objects.prefetch_related('values').all()
    serializer_class = AttributeSerializer
    pagination_class = None

class ProductCategoryListView(generics.ListAPIView):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

class ProjectListAPIView(generics.ListAPIView):
    serializer_class = ProjectSerializer
    def get_queryset(self):
        queryset = Project.objects.all().order_by('-date_completed')
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        return queryset

class ProjectCategoryListView(generics.ListAPIView):
    queryset = ProjectCategory.objects.all()
    serializer_class = ProjectCategorySerializer
    pagination_class = None

class ContactInquiryCreateView(generics.CreateAPIView):
    queryset = ContactInquiry.objects.all()
    serializer_class = ContactInquirySerializer

class CreatePaymentIntentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        cart_items = request.data.get('items', [])
        customer_details = request.data.get('customer_details', {})
        coupon_code = request.data.get('coupon_code', None)
        if not cart_items: 
            return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        order = None
        try:
            # 1. Calculate Subtotal
            subtotal = Decimal('0.00')
            product_ids = [item.get('id') for item in cart_items]
            products_in_db = Product.all_products.filter(id__in=product_ids).in_bulk()

            order_items_to_create = []
            for item_data in cart_items:
                product_id = item_data.get('id')
                product = products_in_db.get(product_id)
                quantity = item_data.get('quantity')

                if not product:
                    raise Exception(f"Product with ID {product_id} not found.")
                if product.stock < quantity:
                    raise Exception(f"Not enough stock for {product.name}. Only {product.stock} available.")
                
                item_cost = product.price * quantity
                subtotal += item_cost
                order_items_to_create.append(OrderItem(product=product, price=product.price, quantity=quantity))

            # 2. Calculate Discount
            coupon_instance = None
            discount_amount = Decimal('0.00')
            if coupon_code:
                coupon_instance = Coupon.objects.get_active_coupon(coupon_code)
                if coupon_instance:
                    discount_amount = (subtotal * Decimal(coupon_instance.discount_percent / 100)).quantize(Decimal('0.01'))
                else:
                    return Response({'error': 'Invalid or expired coupon code.'}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Calculate Shipping and Tax
            shipping_cost = Decimal('0.00') if subtotal > SHIPPING_COST_THRESHOLD else SHIPPING_COST_STANDARD
            tax_amount = (subtotal * TAX_RATE).quantize(Decimal('0.01'))

            # 4. Calculate Grand Total
            grand_total = subtotal + shipping_cost + tax_amount - discount_amount

            # 5. Create Order in DB
            order_data = {
                'user': request.user,
                'first_name': customer_details.get('firstName'),
                'last_name': customer_details.get('lastName'),
                'email': customer_details.get('email'),
                'phone': customer_details.get('phone'),
                'address_line_1': customer_details.get('address_line_1'),
                'address_line_2': customer_details.get('address_line_2'),
                'city': customer_details.get('city'),
                'county_state': customer_details.get('county'),
                'paid': False,
                'subtotal': subtotal,
                'tax': tax_amount,
                'shipping': shipping_cost,
                'coupon': coupon_instance,
                'discount': discount_amount,
                'grand_total': grand_total,
            }
            order = Order.objects.create(**order_data)

            # Create Order Items
            for item in order_items_to_create:
                item.order = order
            OrderItem.objects.bulk_create(order_items_to_create)

            # 6. Create Stripe Payment Intent
            amount_in_cents = int(grand_total * 100)
            if amount_in_cents <= 0:
                raise Exception("Order total must be a positive amount.")

            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency='kes',
                automatic_payment_methods={'enabled': True},
                metadata={'order_id': order.id} # Store DB order ID
            )
            
            return Response({
                'clientSecret': intent.client_secret, 
                'orderId': order.id
            })

        except Product.DoesNotExist:
            if order: 
                order.delete()
            return Response({'error': 'A product in your cart was not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            if order: 
                order.delete()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    def post(self, request):
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        if not webhook_secret: 
            return Response({'error': 'Webhook secret not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try: 
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError): 
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            order_id = payment_intent.metadata.get('order_id')
            if order_id:
                try:
                    order = Order.objects.get(id=order_id)
                    if not order.paid:  # Prevent double processing
                        order.paid = True
                        order.save()
                        # Decrease stock
                        for item in order.items.all():
                            product = item.product
                            if product and product.stock >= item.quantity:
                                product.stock -= item.quantity
                                product.save()
                except Order.DoesNotExist:
                    print(f"Webhook Error: Order with ID {order_id} not found.")
        return Response(status=status.HTTP_200_OK)

class ValidateCartView(APIView):
    def post(self, request, *args, **kwargs):
        product_ids = request.data.get('product_ids', [])
        if not product_ids:
            return Response([], status=status.HTTP_200_OK)
        
        products = Product.objects.filter(id__in=product_ids)
        
        # Pass request context to serializer
        serializer = ProductSerializer(
            products, 
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(user=user)

class OrderHistoryView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return self.request.user.orders.all().order_by('-created_at')

class BlogPageViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    
    def list(self, request):
        featured_post = BlogPost.objects.filter(is_featured=True).first() or BlogPost.objects.order_by('-published_date').first()
        posts_queryset = BlogPost.objects.all()
        if featured_post: 
            posts_queryset = posts_queryset.exclude(id=featured_post.id)
            
        categories = BlogCategory.objects.all()
        data = {
            'featured_post': BlogPostSerializer(featured_post).data if featured_post else None,
            'posts': BlogPostSerializer(posts_queryset, many=True).data,
            'categories': BlogCategorySerializer(categories, many=True).data
        }
        return Response(data)

class BlogPostDetailView(generics.RetrieveAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]

class RelatedPostsView(generics.ListAPIView):
    serializer_class = BlogPostSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        category_slug = self.kwargs['category_slug']
        exclude_id = self.request.query_params.get('exclude')
        queryset = BlogPost.objects.filter(category__slug=category_slug).exclude(is_featured=True)
        if exclude_id is not None: 
            queryset = queryset.exclude(id=exclude_id)
        return queryset.order_by('-published_date')[:3]

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsSuperUser])
def admin_stats(request):
    try: 
        days = int(request.query_params.get('days', '30'))
    except (ValueError, TypeError): 
        days = 30
        
    start_date = timezone.now() - timedelta(days=days)
    paid_items = OrderItem.objects.filter(order__paid=True)
    paid_items_with_profit = paid_items.annotate(
        cost_of_goods=Coalesce(F('product__buying_price'), Value(0), output_field=DecimalField()) * F('quantity')
    ).annotate(
        profit=F('price') * F('quantity') - F('cost_of_goods')
    )
    
    core_stats = paid_items_with_profit.aggregate(
        total_revenue=Sum(F('price')*F('quantity')),
        total_profit=Sum('profit')
    )
    
    total_revenue = core_stats.get('total_revenue') or 0
    total_profit = core_stats.get('total_profit') or 0
    total_orders = Order.objects.filter(paid=True).count()
    
    sales_over_time_raw = paid_items_with_profit.filter(
        order__created_at__gte=start_date
    ).annotate(date=TruncDate('order__created_at')).values('date').annotate(
        daily_revenue=Sum(F('price')*F('quantity')),
        daily_profit=Sum('profit')
    ).order_by('date')
    
    paid_orders = Order.objects.filter(paid=True, created_at__gte=start_date)
    orders_over_time_raw = paid_orders.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        order_count=Count('id'),
        customer_count=Count('user__id', distinct=True)
    ).order_by('date')
    
    top_products = paid_items.values('product__name').annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(F('price')*F('quantity'))
    ).order_by('-total_sold')[:5]
    
    low_stock_products = Product.objects.filter(stock__lte=10, stock__gt=0).order_by('stock')
    out_of_stock_count = Product.objects.filter(stock=0).count()
    
    inventory_value_agg = Product.objects.filter(buying_price__isnull=False).aggregate(
        total_value=Sum(F('stock')*F('buying_price'))
    )
    inventory_value = inventory_value_agg['total_value'] or 0
    
    data = {
        'total_revenue': f"{total_revenue:.2f}",
        'total_profit': f"{total_profit:.2f}",
        'total_orders': total_orders,
        'sales_over_time': [{
            'date': i['date'].strftime('%Y-%m-%d'),
            'revenue': f"{i['daily_revenue']:.2f}",
            'profit': f"{i.get('daily_profit', 0):.2f}"
        } for i in sales_over_time_raw],
        'orders_over_time': [{
            'date': i['date'].strftime('%Y-%m-%d'),
            'order_count': i['order_count'],
            'customer_count': i['customer_count']
        } for i in orders_over_time_raw],
        'top_selling_products': [{
            'product__name': i['product__name'],
            'total_sold': i['total_sold'],
            'total_revenue': float(i['total_revenue'] or 0)
        } for i in top_products],
        'low_stock_products': list(low_stock_products.values('name', 'stock')),
        'out_of_stock_count': out_of_stock_count,
        'total_inventory_value': f"{inventory_value:.2f}"
    }
    return Response(data)

class AdminProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='category__id')
    stock = django_filters.CharFilter(method='filter_by_stock')

    class Meta:
        model = Product
        fields = ['category', 'stock']

    def filter_by_stock(self, queryset, name, value):
        if value == 'low':
            return queryset.filter(stock__lte=5, stock__gt=0)
        if value == 'out':
            return queryset.filter(stock=0)
        return queryset

class AdminProductListView(generics.ListAPIView):
    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = AdminProductFilter
    search_fields = ['name', 'description', 'sku']
    pagination_class = None
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class AdminProductDetailView(generics.DestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]

class AdminUserFilter(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = User
        fields = ['is_active']

class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    filter_backends = [django_filters.DjangoFilterBackend, filters.SearchFilter]
    filterset_class = AdminUserFilter
    search_fields = ['username', 'first_name', 'last_name', 'email']
    pagination_class = None