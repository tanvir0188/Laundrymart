
from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import VerifyOTPView, ResendOTPView, forget_password_otp, ChangePasswordAPIView

urlpatterns = [
    path('login', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-otp', VerifyOTPView.as_view(), name='verify_otp'),
    path('resend-otp', ResendOTPView.as_view(), name='resend_otp'),
    path('forget-password', forget_password_otp, name='forget_password'),
    path('change-password', ChangePasswordAPIView.as_view(), name='password_change'),

    path('register', views.RegisterView.as_view(), name='register'),
    path('logout', views.LogoutAPIView.as_view(), name='logout'),
]