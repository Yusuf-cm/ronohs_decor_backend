# users/urls.py

from django.urls import path
from .views import (
    RegisterView, 
    MyTokenObtainPairView, 
    CurrentUserView, 
    UsernameSuggestionView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordResetValidateTokenView, # <-- Import the new view
    AdminUserListView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('token/', MyTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('me/', CurrentUserView.as_view(), name='current-user'),
    path('username/suggest/', UsernameSuggestionView.as_view(), name='username-suggest'),
    
    # Password Reset URLs
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    # --- NEW: Token Validation URL ---
    path('password-reset/validate-token/', PasswordResetValidateTokenView.as_view(), name='password-reset-validate'),
    
    # Admin
    path('all/', AdminUserListView.as_view(), name='admin-user-list'),
]
