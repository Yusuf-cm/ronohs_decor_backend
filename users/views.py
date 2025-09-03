# users/views.py

from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
import random

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    RegisterSerializer, 
    UserSerializer, 
    PasswordResetRequestSerializer, 
    PasswordResetConfirmSerializer,
    MyTokenObtainPairSerializer,
    AdminUserListSerializer
)
from api.permissions import IsSuperUser 

# --- UPDATED: MyTokenObtainPairView with Email Login Logic ---
class MyTokenObtainPairView(TokenObtainPairView):
    """
    Handles user login via username OR email and returns access and refresh tokens.
    """
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # Get the identifier the user provided
        identifier = request.data.get('username')

        # Check if the identifier looks like an email address
        if '@' in identifier:
            try:
                # Find the user by their email address
                user = User.objects.get(email__iexact=identifier)
                # IMPORTANT: Replace the identifier in the request with the user's actual username
                # before passing it to the default authentication logic.
                request.data['username'] = user.username
            except User.DoesNotExist:
                # If no user is found with that email, let the authentication fail normally
                # by proceeding with the original (non-existent) username.
                pass
        
        # The parent's post method will now handle authentication with the correct username
        return super().post(request, *args, **kwargs)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({"detail": "User registered successfully."}, status=status.HTTP_201_CREATED, headers=headers)

class CurrentUserView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    def get_object(self): return self.request.user

class UsernameSuggestionView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '').strip()
        if not username: return Response({'error': 'Username cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
        if not User.objects.filter(username__iexact=username).exists(): return Response({'suggestions': []})
        suggestions = []
        for _ in range(3):
            random_suffix = ''.join([str(random.randint(0, 9)) for _ in range(3)])
            suggestion = f"{username}{random_suffix}"
            while User.objects.filter(username__iexact=suggestion).exists():
                 random_suffix = ''.join([str(random.randint(0, 9)) for _ in range(3)])
                 suggestion = f"{username}{random_suffix}"
            suggestions.append(suggestion)
        return Response({'suggestions': suggestions})

class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email).first()
        if user:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0] if settings.CORS_ALLOWED_ORIGINS else ''
            reset_link = f"{frontend_url}/reset-password/{uid}/{token}"
            subject = "Password Reset for Your Ronohs Decor Account"
            message = f"Hi {user.first_name or user.username},\n\nYou requested a password reset. Please click the link below to set a new password:\n{reset_link}\n\nIf you did not request this, please ignore this email.\n\nThanks,\nThe Ronohs Decor Team"
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
        return Response({"detail": "If an account with this email exists, a password reset link has been sent."}, status=status.HTTP_200_OK)

class PasswordResetValidateTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        uidb64 = request.data.get('uid'); token = request.data.get('token')
        if not uidb64 or not token: return Response({"detail": "UID and token are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            uid = urlsafe_base64_decode(uidb64).decode(); user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist): user = None
        if user is not None and default_token_generator.check_token(user, token):
            return Response({"detail": "Token is valid."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid or expired token.", "code": "token_expired"}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = urlsafe_base64_decode(data['uid']).decode(); user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist): user = None
        if user is not None and default_token_generator.check_token(user, data['token']):
            form = SetPasswordForm(user, data)
            if form.is_valid():
                form.save(); return Response({"detail": "Password has been reset successfully."}, status=status.HTTP_200_OK)
            else:
                return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperUser]
    pagination_class = None
