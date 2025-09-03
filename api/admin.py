# In api/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    Category, Product, Project, ContactInquiry, Order, OrderItem, 
    BlogPost, Author, BlogCategory, Coupon, ProjectCategory,
    Attribute, AttributeValue, ProductImage, SiteConfiguration, Testimonial
)

# --- Attribute Admins ---
class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1

@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [AttributeValueInline]

# --- Coupon Admin ---
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'is_active', 'valid_from', 'valid_to')
    list_filter = ('is_active',)
    search_fields = ('code',)

# --- Author Admin ---
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name',)

# --- Category Admins ---
admin.site.register(Category)

@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    def get_prepopulated_fields(self, request, obj=None):
        return {'slug': ('name',)}

# --- NEW: Inline for multiple product images ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # Show one empty slot for a new image by default
    fields = ('image', 'alt_text')

# --- Product Admin ---
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return Product.all_products.all()
    
    list_display = ('name', 'category', 'price', 'stock', 'rating', 'is_featured')
    list_filter = ('category', 'is_featured', 'attributes__value')
    search_fields = ('name', 'description', 'sku')
    list_editable = ('price', 'stock', 'is_featured')
    filter_horizontal = ('attributes',) 
    inlines = [ProductImageInline] # <-- ADDED THIS

# --- BlogPost Admin ---
@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'published_date', 'is_featured')
    list_filter = ('category', 'is_featured', 'published_date')
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_featured', 'category')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'category', 'is_featured')}),
        ('Content', {'fields': ('featured_image', 'excerpt', 'content')}),
        ('Metadata', {'fields': ('author',)})
    )

# --- Project Admin ---
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date_completed', 'is_featured')
    list_filter = ('is_featured', 'category',)
    search_fields = ('title', 'description')

# --- Contact Inquiry Admin ---
@admin.register(ContactInquiry)
class ContactInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'sent_at')
    readonly_fields = ('name', 'email', 'message', 'sent_at')
    search_fields = ('name', 'email', 'message')

# --- Order Admin ---
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    readonly_fields = ('product', 'price', 'quantity')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'grand_total', 'paid', 'delivery_status', 'created_at']
    list_filter = ['paid', 'delivery_status', 'created_at', 'payment_method']
    search_fields = ['id', 'first_name', 'last_name', 'email', 'user__username']
    inlines = [OrderItemInline]
    list_editable = ['delivery_status']
    
    readonly_fields = (
        'id', 'user', 'created_at', 'payment_method', 
        'first_name', 'last_name', 'email', 'phone', 
        'address_line_1', 'address_line_2', 'city', 'county_state',
        'subtotal', 'shipping', 'tax', 'coupon', 'discount', 'grand_total', 'paid'
    )
    
    fieldsets = (
        ('Order Information', {'fields': ('id', 'user', 'created_at')}),
        ('Status', {'fields': ('paid', 'delivery_status', 'estimated_delivery')}),
        ('Financials', {'fields': ('subtotal', 'shipping', 'tax', 'coupon', 'discount', 'grand_total')}),
        ('Payment', {'fields': ('payment_method',)}),
        ('Shipping Details', {'fields': ('first_name', 'last_name', 'email', 'phone', 'address_line_1', 'address_line_2', 'city', 'county_state')})
    )

    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return True

# --- User Admin ---
class OrderInlineForUser(admin.TabularInline):
    model = Order
    extra = 0
    fields = ('id', 'grand_total', 'paid', 'created_at')
    readonly_fields = ('id', 'grand_total', 'paid', 'created_at')
    show_change_link = True
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

class CustomUserAdmin(BaseUserAdmin):
    inlines = (OrderInlineForUser,)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    # A simple admin interface for the singleton model
    list_display = ('phone_number', 'email_address')

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'project_type', 'rating', 'is_featured')
    list_editable = ('is_featured',)