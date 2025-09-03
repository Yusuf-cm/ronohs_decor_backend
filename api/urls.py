from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProductListAPIView, 
    ProductDetailAPIView, 
    FeaturedProductListAPIView, 
    ProductCategoryListView,
    ProductAttributeListView,
    ValidateCartView,
    ProjectListAPIView, 
    ProjectCategoryListView,
    CreatePaymentIntentView, 
    StripeWebhookView, 
    OrderHistoryView, 
    OrderDetailView,
    ValidateCouponView,
    WishlistDetailView,
    WishlistToggleView,
    BlogPageViewSet, 
    BlogPostDetailView,
    RelatedPostsView,
    admin_stats, 
    AdminProductListView,
    AdminProductDetailView,
    AdminUserListView,
    ContactInquiryCreateView,
    # Only include if implemented:
    # SiteConfigurationView,
    # FeaturedTestimonialsView
)

router = DefaultRouter()
router.register(r'blog', BlogPageViewSet, basename='blog')

urlpatterns = [
    path('', include(router.urls)),
    
    path('products/featured/', FeaturedProductListAPIView.as_view(), name='featured-product-list'),
    path('products/validate-cart/', ValidateCartView.as_view(), name='validate-cart'),
    path('products/', ProductListAPIView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailAPIView.as_view(), name='product-detail'),

    path('product-attributes/', ProductAttributeListView.as_view(), name='product-attribute-list'),
    path('categories/', ProductCategoryListView.as_view(), name='product-category-list'),
    path('coupons/validate/', ValidateCouponView.as_view(), name='validate-coupon'),
    path('wishlist/', WishlistDetailView.as_view(), name='wishlist-detail'),
    path('wishlist/toggle/', WishlistToggleView.as_view(), name='wishlist-toggle'),
    path('projects/', ProjectListAPIView.as_view(), name='project-list'),
    path('project-categories/', ProjectCategoryListView.as_view(), name='project-category-list'),
    path('create-payment-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('orders/history/', OrderHistoryView.as_view(), name='order-history'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('blog/<slug:slug>/', BlogPostDetailView.as_view(), name='blog-detail'),
    path('blog/category/<slug:category_slug>/', RelatedPostsView.as_view(), name='related-posts'),
    path('contact/', ContactInquiryCreateView.as_view(), name='contact-create'),
    
    # Only uncomment if you implement these views:
    # path('config/', SiteConfigurationView.as_view(), name='site-config'),
    # path('testimonials/featured/', FeaturedTestimonialsView.as_view(), name='featured-testimonials'),
    
    path('admin/stats/', admin_stats, name='admin-stats'),
    path('admin/products/all/', AdminProductListView.as_view(), name='admin-product-list'),
    path('admin/products/<int:pk>/delete/', AdminProductDetailView.as_view(), name='admin-product-delete'),
    path('admin/users/all/', AdminUserListView.as_view(), name='admin-user-list'),    
]