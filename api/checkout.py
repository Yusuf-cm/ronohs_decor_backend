from rest_framework import serializers


class CartItemInput(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=1000)


class CustomerInput(serializers.Serializer):
    firstName = serializers.CharField(max_length=100)
    lastName = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    address_line_1 = serializers.CharField(max_length=255)
    address_line_2 = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    city = serializers.CharField(max_length=100)
    county = serializers.CharField(max_length=100)


class CheckoutInput(serializers.Serializer):
    items = CartItemInput(many=True, allow_empty=False)
    customer_details = CustomerInput()
    coupon_code = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)

    def validate_items(self, items):
        ids = [item['id'] for item in items]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError('Each product must appear once; update its quantity instead.')
        return items
