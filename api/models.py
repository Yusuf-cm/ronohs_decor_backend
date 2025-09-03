# backend/api/models.py

from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

# --- Product Manager (No changes) ---
class ProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(stock__gt=0)

# --- Category Model (No changes) ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    def __str__(self): return self.name
    class Meta:
        verbose_name_plural = "Product Categories"

# --- Attribute Models (No changes) ---
class Attribute(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., Color, Material")
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="Unique identifier for filtering (e.g., color, material)")
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self): return self.name

class AttributeValue(models.Model):
    attribute = models.ForeignKey(Attribute, related_name='values', on_delete=models.CASCADE)
    value = models.CharField(max_length=100, help_text="e.g., Blue, Cotton")
    class Meta:
        unique_together = ('attribute', 'value')
    def __str__(self): return f"{self.attribute.name}: {self.value}"

# --- UPDATED: Product Model ---
class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="Stock Keeping Unit")
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Optional: For showing a discount.")
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cost of acquiring the product.")
    stock = models.PositiveIntegerField(default=0)
    
    # --- UPDATED: Replaced JSONField with ImageField ---
    main_image = models.ImageField(upload_to='products/', null=True, blank=True, help_text="The main image for the product.")
    
    attributes = models.ManyToManyField(AttributeValue, blank=True, related_name='products')
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    review_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ProductManager() 
    all_products = models.Manager() 
    def __str__(self): return self.name

# --- NEW: Model for handling multiple product images ---
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='additional_images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/additional/')
    alt_text = models.CharField(max_length=255, blank=True, help_text="Descriptive text for SEO and accessibility.")

    def __str__(self):
        return f"Image for {self.product.name}"

# --- Other Models (No changes) ---
class ProjectCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    class Meta: verbose_name_plural = "Project Categories"; ordering = ['name']
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self): return self.name

class Project(models.Model):
    category = models.ForeignKey(ProjectCategory, related_name='projects', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=200, help_text="e.g., 'Modern Apartment Refresh'")
    description = models.TextField(blank=True)
    before_image = models.ImageField(upload_to='projects/', help_text="The 'before' photo")
    after_image = models.ImageField(upload_to='projects/', help_text="The 'after' photo")
    date_completed = models.DateField(null=True, blank=True)
    is_featured = models.BooleanField(default=False, help_text="Feature this on the homepage?")
    def __str__(self): return self.title

class ContactInquiry(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"Inquiry from {self.name} on {self.sent_at.strftime('%Y-%m-%d')}"
    class Meta: verbose_name_plural = "Contact Inquiries"

class CouponManager(models.Manager):
    def get_active_coupon(self, code):
        now = timezone.now()
        try:
            coupon = self.get(code__iexact=code, is_active=True, valid_from__lte=now, valid_to__gte=now)
            return coupon
        except self.model.DoesNotExist:
            return None

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, help_text="The code customers will enter (e.g., WELCOME10)")
    discount_percent = models.PositiveIntegerField(help_text="Discount in percent (e.g., 10 for 10%)")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    objects = CouponManager()
    def __str__(self): return f"{self.code} ({self.discount_percent}%)"
    def clean(self):
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError("The 'valid from' date cannot be after the 'valid to' date.")
        if self.discount_percent > 100:
            raise ValidationError("Discount percentage cannot be more than 100.")
    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)

class Order(models.Model):
    DELIVERY_STATUS_CHOICES = [('processing', 'Processing'), ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')]
    PAYMENT_METHOD_CHOICES = [('stripe', 'Stripe (Credit Card)'), ('mpesa', 'M-Pesa')]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    first_name = models.CharField(max_length=100); last_name = models.CharField(max_length=100); email = models.EmailField(); phone = models.CharField(max_length=20); address_line_1 = models.CharField(max_length=255, blank=True); address_line_2 = models.CharField(max_length=255, blank=True); city = models.CharField(max_length=100, blank=True); county_state = models.CharField(max_length=100, blank=True, verbose_name="County/State")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00); tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00); shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0.00); coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True); discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total discount amount applied"); grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True); paid = models.BooleanField(default=False); payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='stripe'); delivery_status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='processing'); estimated_delivery = models.DateField(null=True, blank=True)
    class Meta: ordering = ('-created_at',)
    def __str__(self): return f"Order {self.id} - Ksh{self.grand_total}"
    def get_total_cost(self): return self.grand_total

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    def __str__(self): return str(self.id)
    def get_cost(self): return self.price * self.quantity

class Author(models.Model):
    name = models.CharField(max_length=100, unique=True); bio = models.TextField(blank=True); avatar = models.ImageField(upload_to='authors/', blank=True, null=True); social_links = models.JSONField(blank=True, null=True, help_text="e.g. {'twitter': 'url', 'linkedin': 'url'}")
    def __str__(self): return self.name

class BlogCategory(models.Model):
    name = models.CharField(max_length=100, unique=True); slug = models.SlugField(max_length=100, unique=True, blank=True)
    class Meta: verbose_name_plural = "Blog Categories"
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    def __str__(self): return self.name

class BlogPost(models.Model):
    category = models.ForeignKey(BlogCategory, related_name='posts', on_delete=models.SET_NULL, null=True, blank=True); title = models.CharField(max_length=200); slug = models.SlugField(max_length=200, unique=True, blank=True); meta_description = models.CharField(max_length=255, blank=True, help_text="Brief description for search engines."); excerpt = models.TextField(blank=True, help_text="A short summary of the article for list views."); content = models.TextField(); author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True); published_date = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True); featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True); image_caption = models.CharField(max_length=255, blank=True, help_text="Optional caption for the featured image."); is_featured = models.BooleanField(default=False, help_text="Feature this post at the top of the blog page? (Only one should be featured at a time)")
    class Meta: ordering = ['-published_date']
    def __str__(self): return self.title
    def save(self, *args, **kwargs):
        if not self.slug: self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class Wishlist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wishlist_profile')
    products = models.ManyToManyField(Product, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f"{self.user.username}'s Wishlist"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_wishlist(sender, instance, created, **kwargs):
    if created:
        Wishlist.objects.create(user=instance)

class SiteConfiguration(models.Model):
    # Business Info
    phone_number = models.CharField(max_length=20, blank=True)
    email_address = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    
    # Social Links
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    
    # Dynamic Stats (for homepage)
    projects_completed = models.PositiveIntegerField(default=500)
    client_satisfaction_percent = models.PositiveIntegerField(default=98, validators=[MaxValueValidator(100)])
    years_of_experience = models.PositiveIntegerField(default=15)

    def save(self, *args, **kwargs):
        # Enforce a single instance of this model
        self.pk = 1
        super(SiteConfiguration, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Prevent deletion
        pass

    @classmethod
    def load(cls):
        # Get or create the single instance
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Site Configuration"

class Testimonial(models.Model):
    client_name = models.CharField(max_length=100)
    project_type = models.CharField(max_length=100, help_text="e.g., Nairobi Residence Project")
    quote = models.TextField()
    rating = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_featured = models.BooleanField(default=False, help_text="Show this on the homepage?")
    avatar = models.ImageField(upload_to='testimonials/', null=True, blank=True)
    
    def __str__(self):
        return f"Testimonial from {self.client_name}"