from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Route all traffic to the accounts app
    path('', include('market.urls')), 
    
    # Optional: Redirect root URL (/) to login automatically
    path('', lambda request: redirect('login')),
]