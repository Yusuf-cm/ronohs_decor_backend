# api/serializers.py

from rest_framework import serializers
from .models import (
    Category, Product, Project, ContactInquiry, Order, OrderItem, 
    BlogPost, BlogCategory, Author, ProjectCategory,
    Attribute, AttributeValue, Wishlist, ProductImage
)

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ProjectCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectCategory
        fields = ['id', 'name', 'slug']

class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ['id', 'value']

class AttributeSerializer(serializers.ModelSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)
    class Meta:
        model = Attribute
        fields = ['name', 'slug', 'values']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    attributes = AttributeValueSerializer(many=True, read_only=True)
    
    # Custom field to combine all image URLs
    images = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'category', 'description', 
            'price', 'original_price', 'stock', 
            'main_image', # Keep main_image for direct access
            'images', # List of all image URLs
            'attributes', 'rating', 'review_count', 'is_featured', 
            'created_at', 'buying_price'
        ]

    def get_images(self, obj):
        request = self.context.get('request')
        images_urls = []
        
        # Add main image if it exists
        if obj.main_image and hasattr(obj.main_image, 'url'):
            if request:
                images_urls.append(request.build_absolute_uri(obj.main_image.url))
            else:
                # Fallback for cases without request context
                images_urls.append(obj.main_image.url)
        
        # Add all additional images
        additional_images = obj.additional_images.all()
        for img in additional_images:
            if img.image and hasattr(img.image, 'url'):
                if request:
                    images_urls.append(request.build_absolute_uri(img.image.url))
                else:
                    images_urls.append(img.image.url)
                    
        return images_urls

class WishlistSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['user', 'products']

class ProjectSerializer(serializers.ModelSerializer):
    category = ProjectCategorySerializer(read_only=True)
    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'before_image', 'after_image', 'date_completed', 'is_featured', 'category']

class ContactInquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInquiry
        fields = ['name', 'email', 'message']
    
    def validate_message(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True, allow_null=True)
    class Meta:
        model = Order
        fields = [
            'id', 'user', 'first_name', 'last_name', 'email', 'phone', 
            'address_line_1', 'address_line_2', 'city', 'county_state', 
            'items', 'created_at', 'paid', 
            'subtotal', 'shipping', 'tax', 'discount', 'grand_total', 'coupon_code',
            'payment_method', 'delivery_status', 'estimated_delivery'
        ]

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['name', 'bio', 'avatar', 'social_links']

class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ['name', 'slug']

class BlogPostSerializer(serializers.ModelSerializer):
    category = BlogCategorySerializer(read_only=True)
    author = AuthorSerializer(read_only=True)
    class Meta:
        model = BlogPost
        fields = [
            'id', 'title', 'slug', 'content', 'excerpt', 'author', 
            'published_date', 'updated_at', 'featured_image', 'image_caption', 
            'category', 'is_featured', 'meta_description'
        ]