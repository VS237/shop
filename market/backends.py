from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .supabase_client import supabase

class SupabaseBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        try:
            # 1. Attempt to sign in with Supabase
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # 2. If successful, get/create user in Django DB
            user_data = res.user
            user, created = User.objects.get_or_create(
                username=user_data.email, # Use email as username
                email=user_data.email
            )
            return user
        except Exception:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None