from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .supabase_client import supabase
from django.contrib.auth import logout as django_logout

# 1. Standard Library Imports
import os
import json
import uuid
from decimal import Decimal
from datetime import timedelta
from dotenv import load_dotenv

# 2. Third-Party Libraries (OpenAI, etc.)
from openai import OpenAI

# 3. Django Core Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib import messages

# 4. Django Auth & Decorators
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required

# 5. Django Database & Query Imports
from django.db import models, transaction, IntegrityError
from django.db.models import (
    Sum, Count, Avg, F, Q, 
    ExpressionWrapper, DecimalField, fields
)
from django.db.models.functions import TruncDay, TruncMonth, TruncYear

# 6. Local App Imports (Mom'shop Models and Forms)
from .models import (
    Product, Category, Supplier, Seller, 
    Customer, Order, OrderItem, Sale, 
    Expenses, SalesReport, Credit
)
from .forms import (
    CustomerRegistrationForm, ProductForm, 
    SellerForm, ExpensesForm
)

#___________________CUSTOMER/VISITOR SECTION______________
def signup_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Supabase sends a 6-digit code to the email provided
            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })
            
            if response.user:
                # Store email in session to use on the verification page
                request.session['unverified_email'] = email
                messages.info(request, "A verification code has been sent to your email.")
                return redirect('verify_code')
                
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            
    return render(request, 'signup.html')

def user_register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            # Get data from form but don't save to Django DB yet
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            
            try:
                # 1. Register the user in Supabase Auth
                # This triggers the 6-digit code via Resend/SMTP
                response = supabase.auth.sign_up({
                    "email": email,
                    "password": password,
                })

                if response.user:
                    # 2. Save the Django Customer record (local DB)
                    # We set is_active=False until they verify the code
                    customer = form.save(commit=False)
                    if hasattr(customer, 'is_active'):
                        customer.is_active = False 
                    customer.save()

                    # 3. Store email in session for the verification view
                    request.session['unverified_email'] = email
                    
                    messages.success(request, f'Registration successful! Please enter the 6-digit code sent to {email}.')
                    return redirect('verify_code') # Redirect to your OTP entry page

            except Exception as e:
                error_msg = str(e)
                if "confirmation email" in error_msg.lower():
                    messages.error(request, "Mail Error: We couldn't send the code. Please check if our email domain is verified.")
                else:
                    messages.error(request, f"Supabase Error: {error_msg}")
                # Stay on form if Supabase fails
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'register.html', {'form': form})

def verify_code_view(request):
    email = request.session.get('unverified_email')
    
    if not email:
        messages.error(request, "invalid email. Please register again.")
        return redirect('register')

    if request.method == "POST":
        token = request.POST.get('otp_code')
        
        try:
            # Verify the 6-digit code (OTP)
            response = supabase.auth.verify_otp({
                "email": email,
                "token": token,
                "type": "signup"
            })
            
            if response.session:
                messages.success(request, "Email verified successfully! You can now log in.")
                del request.session['unverified_email'] # Clean up
                return redirect('login')
                
        except Exception as e:
            messages.error(request, "Invalid or expired code.")
            
    return render(request, 'verify_code.html', {'email': email})

def user_login(request):
    if request.method == "POST":
        user_identifier = request.POST.get("user")
        password = request.POST.get("password")

        # Try to authenticate with username first
        user = authenticate(request, username=user_identifier, password=password)
        
        # If authentication fails, check if it might be an email
        if user is None and '@' in user_identifier:
            try:
                user_obj = User.objects.get(email=user_identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass  # User doesn't exist with this email

        if user is not None:
            login(request, user)
            
            if hasattr(user, 'seller'):
                seller = user.seller
                if seller.is_active:
                    return redirect('seller_dashboard')  # Redirect seller to seller dashboard
                else:
                    messages.error(request, "Your seller account is deactivated.")
                    return redirect('login')
            else:
                # Default redirect for users without specific profiles
                messages.success(request, f"Welcome back, {user.first_name}!" if user.first_name else "Welcome back!")
                return redirect('home')
             
        else:
            messages.error(request, "Invalid username/email or password")
            return redirect('login')

    return render(request, 'login.html')

# views.py
from django.shortcuts import redirect
from django.contrib import messages
# Import your utility functions for generating/sending OTP

from django.shortcuts import redirect
from django.contrib import messages
# Import your actual helper functions here
# from .utils import generate_otp, send_otp_email 

def resend_otp(request):
    # 1. Retrieve the email from the session
    email = request.session.get('email') # Double-check this key name matches your Register view!
    
    if not email:
        messages.error(request, "We couldn't find your session. Please register again.")
        return redirect('register')

    try:
        # 2. ACTUALLY generate and send the code
        # code = generate_otp()
        # send_otp_email(email, code)
        
        messages.success(request, f"Success! A new code was sent to {email}.")
        
    except Exception as e:
        messages.error(request, "Failed to send email. Please try again in a moment.")
        # Log the error for your internal debugging
        print(f"SMTP Error: {e}") 

    # 3. Redirect to the VERIFICATION page (ensure this name matches your urls.py)
    return redirect('verify_code')

def logout_view(request):
    # 1. Sign out from Supabase (invalidates the Supabase session)
    try:
        supabase.auth.sign_out()
    except Exception:
        # Fail silently if Supabase session is already gone
        pass

    # 2. Sign out from Django (clears local cookies and session)
    django_logout(request)
    
    # 3. Redirect to login page
    return redirect('login')

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email')
        # Supabase sends the recovery email
        # The 'redirect_to' should be your password update page
        supabase.auth.reset_password_for_email(email, {
            "redirect_to": "https://momshop-c79n.onrender.com/update-password/"
        })
        return render(request, 'forgot_password.html', {"msg": "Check your email!"})
    return render(request, 'forgot_password.html')

from supabase_auth.errors import AuthApiError

from django.contrib.auth.models import User
from django.shortcuts import render
from supabase.lib.client_options import ClientOptions

def update_password(request):
    if request.method == "POST":
        new_password = request.POST.get('new_password')
        access_token = request.POST.get('access_token')
        refresh_token = request.POST.get('refresh_token')

        if access_token and refresh_token:
            try:
                # 1. Establish the session
                session_resp = supabase.auth.set_session(access_token, refresh_token)
                
                # 2. Verify the session is actually active
                user_resp = supabase.auth.get_user()
                if user_resp.user:
                    email = user_resp.user.email
                    
                    # 3. Update Supabase Cloud Password
                    supabase.auth.update_user({"password": new_password})
                    
                    # 4. CRITICAL: Update Django Local Password
                    # This ensures you can actually log in with the new password
                    try:
                        local_user = User.objects.get(email=email)
                        local_user.set_password(new_password)
                        local_user.save()
                    except User.DoesNotExist:
                        # If user doesn't exist locally, you might want to create them 
                        # or just log the error
                        print(f"User {email} updated in Supabase but not found in Django.")

                    return render(request, 'password_reset_complete.html')
                else:
                    return render(request, 'update_password.html', {"msg": "Invalid Session."})
            
            except Exception as e:
                print(f"Password Update Error: {e}")
                return render(request, 'update_password.html', {"msg": "Something went wrong. Please try again."})
        
        return render(request, 'update_password.html', {"msg": "Session data missing."})

    return render(request, 'update_password.html')

def password_reset_complete(request):
    return render(request, 'password_reset_complete.html')

def home(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    
    # Base Queryset
    random_product = Product.objects.order_by('?').first()
    products = Product.objects.filter(quantity__gt=0).order_by('-created_at')

    # Apply Search Filter
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    # Apply Category Filter
    if category_slug:
        products = products.filter(category__name__iexact=category_slug.replace('-', ' '))

    # Pagination (9 products per page)
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    
    return render(request, 'home.html', {
        'products': page_obj,
        'random_product': random_product,
        'categories': categories,
        'query': query,
        'current_category': category_slug
    })

def shop(request):
    query = request.GET.get('q', '')
    category_slug = request.GET.get('category', '')
    
    # Base Queryset
    products = Product.objects.filter(quantity__gt=0).order_by('-created_at')

    # Apply Search Filter
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )

    # Apply Category Filter
    if category_slug:
        products = products.filter(category__name__iexact=category_slug.replace('-', ' '))

    # Pagination (9 products per page)
    paginator = Paginator(products, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    
    return render(request, 'shop.html', {
        'products': page_obj,
        'categories': categories,
        'query': query,
        'current_category': category_slug
    })

@login_required
def my_credit_dashboard(request):
    # Retrieve the customer profile associated with the logged-in user
    try:
        customer = request.user.customer 
    except AttributeError:
        # Handle cases where a User (like an Admin) doesn't have a Customer profile
        return render(request, 'errors/no_profile.html')

    # Get all credits for this customer
    my_credits = customer.credits.all().order_by('-credit_date')
    
    # Calculate total outstanding debt
    my_total_debt = my_credits.filter(
        status__in=['active', 'overdue']
    ).aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'customer': customer,
        'credits': my_credits,
        'total_debt': my_total_debt,
    }
    return render(request, 'my_dashboard.html', context)

def add_to_cart(request, product_id):
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    
    # Logic to add to cart
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    request.session['cart'] = cart
    request.session.modified = True

    # Calculate new total items for the navbar badge
    total_items = sum(int(qty) for qty in cart.values())

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'message': 'Product added to cart!',
            'total_items': total_items
        })

    return redirect('cart')

def cart(request):
    cart_session = request.session.get('cart', {})
    cart_items = []
    subtotal = Decimal('0.00')
    shipping_fee = Decimal('1000.00') # Defined shipping fee

    # 1. Prepare display data for the template
    for p_id, qty in cart_session.items():
        product = get_object_or_404(Product, id=p_id)
        total_price = Decimal(str(product.selling_price)) * int(qty)
        subtotal += total_price
        cart_items.append({
            'product': product,
            'quantity': qty,
            'total_price': total_price,
        })

    # Calculate final total including shipping
    grand_total = subtotal + shipping_fee

    # 2. Handle Order Placement (POST)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "Please log in to place an order.")
            return redirect('login')

        if cart_items:
            customer = get_object_or_404(Customer, user=request.user)
            transaction_id = str(uuid.uuid4())[:8].upper()

            # Create ONE Parent Order with the shipping included in total_amount
            order = Order.objects.create(
                order_number=transaction_id,
                customer=customer,
                total_amount=grand_total, # This now includes the 1000 XAF
                city=request.POST.get('city'),
                town=request.POST.get('town'),
                phone_number=request.POST.get('phone')
            )

            # Create multiple Child OrderItems
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price_at_purchase=item['product'].selling_price
                )

            request.session['cart'] = {}
            request.session.modified = True
            
            return redirect('order_success', order_number=transaction_id) 
        
        else:
            messages.warning(request, "Your cart is empty.")
            return redirect('cart')

    # 3. Handle Page Display (GET)
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,        # Pass subtotal separately
        'shipping_fee': shipping_fee, # Pass shipping fee
        'grand_total': grand_total    # Pass the final sum
    })

def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id_str = str(product_id)

    if product_id_str in cart:
        del cart[product_id_str]
        request.session['cart'] = cart
        request.session.modified = True
    
    return redirect('cart')

def update_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        # Get quantity from the JSON body or POST data
        quantity = int(request.POST.get('quantity', 1))
        product_id_str = str(product_id)
        
        if quantity > 0:
            cart[product_id_str] = quantity
        else:
            cart.pop(product_id_str, None)
            
        request.session['cart'] = cart
        request.session.modified = True
        
        # Calculate new total count
        new_count = sum(cart.values())
        
        return redirect('cart')

def get_cart_count(request):
    cart = request.session.get('cart', {})
    # Sum the quantities of all items in the cart
    total_quantity = sum(cart.values())
    return JsonResponse({'total_quantity': total_quantity})    

def calculate_total(cart):
    total = Decimal('0.00')
    for product_id, quantity in cart.items():
        product = Product.objects.get(id=product_id)
        total += Decimal(str(product.selling_price)) * int(quantity)
    return total

def place_order(request):
    cart = request.session.get('cart', {})
    
    if request.method == 'POST' and cart:
        # 1. Setup basic info
        transaction_id = str(uuid.uuid4())[:8].upper()
        customer = get_object_or_404(Customer, user=request.user)
        
        # Calculate total using Decimal for MySQL accuracy
        total = Decimal('0.00')
        for p_id, qty in cart.items():
            product = Product.objects.get(id=p_id)
            total += Decimal(str(product.selling_price)) * int(qty)

        # 2. CREATE THE ORDER (The Header)
        # NOTICE: We do NOT use 'ordered_product' or 'order_amount' here!
        order = Order.objects.create(
            order_number=transaction_id,
            customer=customer,
            total_amount=total,
            city=request.POST.get('city'),
            town=request.POST.get('town'),
            phone_number=request.POST.get('phone')
        )

        # 3. CREATE THE ITEMS (The Details)
        for product_id, quantity in cart.items():
            product = Product.objects.get(id=product_id)
            
            # This is where your individual product info now lives
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price_at_purchase=product.selling_price
            )

        # 4. Cleanup
        request.session['cart'] = {}
        request.session.modified = True
        
        return redirect('print_receipt', order_number=transaction_id)

    return redirect('cart')

def order_success(request, order_number):
    return render(request, 'order_success.html', {'order_number': order_number})

def print_receipt(request, order_number):
    # Fetch the parent order
    order = get_object_or_404(Order, order_number=order_number)
    
    # Fetch children items linked to this order
    order_items = order.items.all() 

    return render(request, 'receipt.html', {
        'order': order,
        'order_items': order_items,
    })

def contact(request):
    return render(request, 'contact.html')

def about(request):
    return render(request, 'about.html')    

def product_details(request, pk):  # Ensure 'pk' is here!
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_details.html', {'product': product})

def profile(request):
    return render(request, 'profile.html')


#___________________ADMINISTRATOR SECTION_________________

# This function returns True only if the user is a superuser
def is_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin, login_url='login')
def dashboard_home(request):
    # Calculate timeframe for the chart (Last 15 days)
    today = timezone.now()
    chart_start_date = today - timedelta(days=15)

    # 1. Daily Sales Trend (MODIFIED)
    daily_sales = Sale.objects.filter(sale_date__gte=chart_start_date) \
        .annotate(day=TruncDay('sale_date')) \
        .values('day') \
        .annotate(total=Sum('sale_amount')) \
        .order_by('day')

    # Format for Chart.js: "31 Dec"
    sales_labels = [s['day'].strftime("%d %b") if s['day'] else "Unknown" for s in daily_sales]
    sales_data = [float(s['total']) if s['total'] else 0 for s in daily_sales]

    # 2. Top 5 Products (Using your ManyToMany field 'products')
    # We count how many times each product appears across all Sales
    top_products = Sale.objects.values('products__name') \
        .filter(products__name__isnull=False) \
        .annotate(total_sold=Count('products')) \
        .order_by('-total_sold')[:5]

    product_labels = [p['products__name'] for p in top_products]
    product_data = [p['total_sold'] for p in top_products]
    # Calculate dates for the last 30 days
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    
    # --- 1. KPI Calculations ---
    
    # 1. Total Gross Sales (Everything sold: Cash + MoMo + Credit)
    total_sales_qs = Sale.objects.filter(sale_date__gte=thirty_days_ago).aggregate(
        total=Sum('sale_amount')
    )
    total_sales = total_sales_qs['total'] or 0

    # 2. Total Credit Revenue (Revenue you are still waiting to collect)
    # This represents the sale price of the items given on credit
    total_credit_revenue = Credit.objects.filter(
        credit_date__gte=thirty_days_ago
    ).aggregate(total_owed=Sum('amount'))['total_owed'] or 0

    # 3. Total Expenses (Last 30 Days)
    total_expenses_qs = Expenses.objects.filter(
        expenses_date__gte=thirty_days_ago.date()
    ).aggregate(total=Sum('amount'))
    total_expenses = total_expenses_qs['total'] or 0

    # 4. Cost of Credited Stock (The money you spent to buy the items now held as debt)
    credited_stock_cost = Credit.objects.filter(
        credit_date__gte=thirty_days_ago
    ).aggregate(total_cost=Sum('products__buying_price'))['total_cost'] or 0

    # 5. Potential Profit (Paper Profit: Includes credit sales)
    paper_profit_calc = Sale.objects.filter(sale_date__gte=thirty_days_ago).annotate(
        cost_of_goods=F('products__buying_price'),
        item_profit=ExpressionWrapper(F('sale_amount') - F('cost_of_goods'), output_field=fields.DecimalField())
    ).aggregate(total_profit=Sum('item_profit'))
    paper_profit = (paper_profit_calc['total_profit'] or 0) - total_expenses

    # 6. FINAL NET PROFIT (Liquid Profit: Only includes money you actually have)
    # We subtract the full revenue of credits because that cash hasn't entered the system yet.
    net_profit = paper_profit - (total_credit_revenue - credited_stock_cost)
    
    # Active Sellers Count
    active_sellers_count = Seller.objects.count()
    
    # --- 2. Chart Data (Basic Example) ---
    # In a real app, you'd calculate monthly sales and top product units sold here
    # and format them into a JSON structure suitable for Chart.js.

    # Calculate total credit amount for this seller today
    total_credit = Credit.objects.aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'total_sales': total_sales,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'active_sellers_count': active_sellers_count,
        'sales_labels_json': json.dumps(sales_labels),
        'sales_data_json': json.dumps(sales_data),
        'product_labels_json': json.dumps(product_labels),
        'product_data_json': json.dumps(product_data),
        'total_credit': total_credit
        # Placeholder for chart data: 'sales_chart_data': [ ... ],
    }
    return render(request, 'admin/dashboard_home.html', context)

import cloudinary.uploader # Needed for manual deletion
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import F

@user_passes_test(is_admin, login_url='login')
def manage_products(request):
    """
    Comprehensive stock management view - Cloudinary Compatible
    """
    products = Product.objects.all().select_related('category', 'supplier')
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    
    # Search and filter functionality
    category_filter = request.GET.get('category')
    supplier_filter = request.GET.get('supplier')
    search_query = request.GET.get('search')
    
    if category_filter:
        products = products.filter(category_id=category_filter)
    if supplier_filter:
        products = products.filter(supplier_id=supplier_filter)
    if search_query:
        products = products.filter(name__icontains=search_query)
    
    # Low stock alert
    low_stock_count = products.filter(quantity__lte=F('min_stock_level')).count()
    
    context = {
        'products': products,
        'categories': categories,
        'suppliers': suppliers,
        'low_stock_count': low_stock_count,
        'selected_category': category_filter,
        'selected_supplier': supplier_filter,
        'search_query': search_query or '',
    }
    return render(request, 'admin/manage_products.html', context)

@user_passes_test(is_admin, login_url='login')
def add_product(request, product_id=None):
    """
    Add or edit product information with Cloudinary support
    """
    product = None
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        page_title = f"Edit Product: {product.name}"
        success_message = f"Product '{product.name}' updated successfully!"
    else:
        page_title = "Add New Product"
        success_message = "Product added successfully!"
    
    if request.method == 'POST':
        # Ensure request.FILES is passed so Cloudinary picks up the image
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            try:
                product = form.save(commit=False)
                if not product_id:
                    product.created_by = request.user
                
                product.save() # Cloudinary upload happens here automatically
                
                messages.success(request, success_message)
                
                if 'save_and_add_another' in request.POST:
                    return redirect('add_product')
                elif 'save_and_continue' in request.POST and product_id:
                    return redirect('edit_product', product_id=product.id)
                else:
                    return redirect('manage_products')
                    
            except Exception as e:
                messages.error(request, f"Cloudinary Upload Error: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
        'page_title': page_title,
    }
    return render(request, 'admin/add_product.html', context)

@user_passes_test(is_admin, login_url='login')
def product_delete(request, product_id=None):
    """
    Deletes a Product object and its remote image from Cloudinary.
    """
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        # 1. Delete image from Cloudinary if it exists
        if product.image:
            try:
                # We use the public_id to tell Cloudinary which file to delete
                cloudinary.uploader.destroy(product.image.public_id)
            except Exception as e:
                # We log the error but continue deleting the product record
                print(f"Cloudinary deletion failed: {e}")
        
        # 2. Delete database record
        product.delete()
        
        messages.success(request, f'Product {product.name} deleted successfully!')
        return redirect('manage_products') 
    
    return render(request, 'admin/product_delete.html', {'product': product})

@user_passes_test(is_admin, login_url='login')
def delete_all_sales(request):
    if request.method == "POST":
        # Filter to ensure the seller only deletes THEIR own sales
        my_sales = Sale.objects.filter()
        count = my_sales.count()
        
        if count > 0:
            my_sales.delete()
            messages.success(request, f"Successfully cleared {count} sales from your record.")
        else:
            messages.info(request, "There were no sales to delete.")
            
        return redirect('dashboard_home')

@user_passes_test(is_admin, login_url='login')
def manage_sellers(request):
    """Admin view to manage all sellers"""
    sellers = Seller.objects.all().select_related('user').order_by('-created_at')
    
    # Search and filter
    search_query = request.GET.get('search')
    status_filter = request.GET.get('status')
    
    if search_query:
        sellers = sellers.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            sellers = sellers.filter(is_active=True)
        elif status_filter == 'inactive':
            sellers = sellers.filter(is_active=False)
    
    context = {
        'sellers': sellers,
        'search_query': search_query or '',
        'status_filter': status_filter or '',
    }
    
    return render(request, 'admin/manage_sellers.html', context)

@user_passes_test(is_admin, login_url='login')
def create_sellers(request):
    """Admin view to create new seller profile"""
    # Check if user has permission to create sellers
    '''if not (request.user.is_superuser or hasattr(request.user, 'administratorprofile')):
        messages.error(request, "You don't have permission to create seller profiles.")
        return redirect('dashboard_home')'''
    
    if request.method == 'POST':
        form = SellerForm(request.POST)
        if form.is_valid():
            try:
                # Check if username already exists
                username = form.cleaned_data['username']
                if User.objects.filter(username=username).exists():
                    messages.error(request, f"❌ Username '{username}' is already taken. Please choose a different username.")
                    return render(request, 'admin/create_sellers.html', {'form': form})
                
                # Check if email already exists
                email = form.cleaned_data['email']
                if User.objects.filter(email=email).exists():
                    messages.error(request, f"❌ Email '{email}' is already registered. Please use a different email address.")
                    return render(request, 'admin/create_sellers.html', {'form': form})
                
                # Check if phone number already exists
                phone = form.cleaned_data['phone']
                if Seller.objects.filter(phone=phone).exists():
                    messages.error(request, f"❌ Phone number '{phone}' is already registered. Please use a different phone number.")
                    return render(request, 'admin/create_sellers.html', {'form': form})
                
                # Check if CNI number already exists
                id_card_number = form.cleaned_data['id_card_number']
                if Seller.objects.filter(id_card_number=id_card_number).exists():
                    messages.error(request, f"❌ CNI number '{id_card_number}' is already registered. Please check the ID card number.")
                    return render(request, 'admin/create_sellers.html', {'form': form})
                
                # Validate password strength
                password = form.cleaned_data['password']
                if len(password) < 8:
                    messages.error(request, "❌ Password must be at least 8 characters long.")
                    return render(request, 'admin/create_sellers.html', {'form': form})
                
                # Create User first
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )
                
                # Create Seller profile
                seller = form.save(commit=False)
                seller.user = user
                
                # Set created_by only if administrator profile exists
                '''if hasattr(request.user, 'administratorprofile'):
                    seller.created_by = request.user.administratorprofile'''
                # For superusers without admin profile, created_by remains null
                
                seller.save()
                
                messages.success(request, f"✅ Seller profile for {user.get_full_name()} created successfully!")
                messages.info(request, f"📧 Login credentials: Username: {username} | Password: {password}")
                
                return redirect('manage_sellers')
                
            except IntegrityError as e:
                # Handle database integrity errors
                if 'user' in locals():
                    user.delete()
                
                if 'unique constraint' in str(e).lower():
                    if 'username' in str(e):
                        messages.error(request, "❌ Database error: Username already exists.")
                    elif 'email' in str(e):
                        messages.error(request, "❌ Database error: Email already exists.")
                    elif 'phone' in str(e):
                        messages.error(request, "❌ Database error: Phone number already exists.")
                    elif 'id_card_number' in str(e):
                        messages.error(request, "❌ Database error: CNI number already exists.")
                    else:
                        messages.error(request, "❌ Database integrity error: Duplicate entry detected.")
                else:
                    messages.error(request, f"❌ Database error: {str(e)}")
                    
            except ValidationError as e:
                if 'user' in locals():
                    user.delete()
                messages.error(request, f"❌ Validation error: {e}")
                
            except Exception as e:
                # Clean up: delete user if seller creation fails
                if 'user' in locals():
                    user.delete()
                
                # Specific error messages for common issues
                error_message = str(e).lower()
                
                if 'password' in error_message:
                    messages.error(request, "❌ Password error: Invalid password format.")
                elif 'email' in error_message:
                    messages.error(request, "❌ Email error: Invalid email format.")
                elif 'phone' in error_message:
                    messages.error(request, "❌ Phone error: Invalid phone number format.")
                elif 'salary' in error_message:
                    messages.error(request, "❌ Salary error: Invalid salary amount.")
                elif 'hire_date' in error_message:
                    messages.error(request, "❌ Hire date error: Invalid date format.")
                else:
                    messages.error(request, f"❌ Unexpected error: {str(e)}")
        else:
            # Show specific form field errors
            for field, errors in form.errors.items():
                field_name = form.fields[field].label if field in form.fields else field
                for error in errors:
                    messages.error(request, f"❌ {field_name}: {error}")
    else:
        form = SellerForm()
    
    context = {
        'form': form,
        'page_title': 'Create New Seller'
    }
    
    return render(request, 'admin/create_sellers.html', context)

@user_passes_test(is_admin, login_url='login')
def edit_sellers(request, seller_id):
    """Admin view to edit existing seller profile and related User data"""
    seller = get_object_or_404(Seller, id=seller_id)
    
    if request.method == 'POST':
        # Added request.FILES to handle profile pictures if your form has them
        form = SellerForm(request.POST, request.FILES, instance=seller)
        
        if form.is_valid():
            # Save the form but don't commit to DB yet if you need to tweak data
            updated_seller = form.save()
            
            messages.success(
                request, 
                f'Seller profile for {updated_seller.user.get_full_name()} updated successfully!'
            )
            return redirect('manage_sellers')
        else:
            # Provide specific feedback if the form fails
            messages.error(request, 'Update failed. Please check the form errors.')
    else:
        # GET request: Pre-fill the form with existing data
        form = SellerForm(instance=seller)
    
    context = {
        'form': form,
        'seller': seller,
        'page_title': f'Edit Seller: {seller.user.get_full_name()}'
    }
    
    return render(request, 'admin/edit_sellers.html', context)

@user_passes_test(is_admin, login_url='login')
def manage_expenses(request):
    """
    Manage and track business expenditures
    """
    expenses = Expenses.objects.all().order_by('-expenses_date')
    
    # Filtering
    expense_type = request.GET.get('type')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if expense_type:
        expenses = expenses.filter(type=expense_type)
    if start_date:
        expenses = expenses.filter(expenses_date__gte=start_date)
    if end_date:
        expenses = expenses.filter(expenses_date__lte=end_date)
    
    if request.method == 'POST':
        form = ExpensesForm(request.POST)
        if form.is_valid():
            expenses = form.save(commit=False)
            #expenses.recorded_by = request.user.administratorprofile
            expenses.save()
            messages.success(request, 'Expenses recorded successfully!')
            return redirect('manage_expenses')
    else:
        form = ExpensesForm()
    
    # Total expenditures for display
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    context = {
        'expenses': expenses,
        'form': form,
        'total_expenses': total_expenses,
        'expense_types': Expenses.EXPENSES_TYPES,
    }
    
    return render(request, 'admin/manage_expenses.html', context)

@user_passes_test(is_admin, login_url='login')
def delete_expenses(request, expenses_id):
    """
    Deletes a Product object, including its associated image file from the server.
    """
    # 1. Fetch the object or return a 404 error if it doesn't exist
    expenses = get_object_or_404(Expenses, id=expenses_id)

    if request.method == 'POST':
        # 2. Check if the product has an image associated with it
        expenses.delete()
        
        # 7. Redirect to the list view or success page
        messages.success(request, f'Product {expenses.expenses_type} deleted successfully!')
        return redirect('manage_expenses') 
    
    # Optional: Render a confirmation template for GET requests
    # If the request is GET, display a confirmation page (e.g., "Are you sure?")
    return render(request, 'admin/delete_expenses.html', {'expenses': expenses})

@user_passes_test(is_admin, login_url='login')
def sales_report(request):
    """
    Displays a history of all daily/monthly sales reports generated.
    """
    # Fetch reports for the logged-in seller, newest first
    reports = SalesReport.objects.filter().order_by('-report_date')
    
    context = {
        'reports': reports,
        'page_title': 'My Sales Reports'
    }
    return render(request, 'admin/sales_report.html', context)

@user_passes_test(is_admin, login_url='login')
def delete_all_reports(request):
    if request.method == "POST":
        # Filter to ensure the seller only deletes THEIR own sales
        my_reports = SalesReport.objects.filter()
        count = my_reports.count()
        
        if count > 0:
            my_reports.delete()
            messages.success(request, f"Successfully cleared {count} reports from your record.")
        else:
            messages.info(request, "There were no report to delete.")
            
        return redirect('sales_report')


def toggle_seller_status(request, seller_id):
    """Activate/Deactivate seller account"""
    seller = get_object_or_404(Seller, id=seller_id)
    
    if request.method == 'POST':
        seller.is_active = not seller.is_active
        seller.save()
        
        action = "activated" if seller.is_active else "deactivated"
        messages.success(request, f'Seller account {action} successfully!')
    
    return redirect('manage_sellers')

@user_passes_test(is_admin, login_url='login')
def seller_sales_report(request, seller_id):
    """View sales report for a specific seller"""
    seller = get_object_or_404(Seller, id=seller_id)
    
    # Date range - default to last 30 days
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Sales data
    sales = Sale.objects.filter(
        seller=seller,
        sale_date__date__range=[start_date, end_date],
        is_completed=True
    ).order_by('-sale_date')
    
    # Statistics
    total_sales = sales.aggregate(
        # FIX 1: Change 'total_revenue' to use the correct field 'sale_amount'
        total_revenue=Sum('sale_amount'), 
        total_transactions=Count('id'),
        # FIX 2: Change 'average_sale' to use the correct field 'sale_amount'
        average_sale=Avg('sale_amount')
    )
    
    # Daily sales trend
    daily_sales = sales.annotate(
        day=TruncDay('sale_date')
    ).values('day').annotate(
        # FIX 3: Change 'daily_revenue' to use the correct field 'sale_amount'
        daily_revenue=Sum('sale_amount'), 
        daily_transactions=Count('id')
    ).order_by('day')
    
    context = {
        'seller': seller,
        'sales': sales,
        'total_sales': total_sales,
        'daily_sales': list(daily_sales),
        'days': days,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'admin/seller_sales_report.html', context)

@user_passes_test(is_admin, login_url='login')
def admin_order(request):
    # Only show orders that haven't been processed yet
    pending_orders = Order.objects.filter(is_processed=False).order_by('-order_date')
    return render(request, 'admin/admin_order.html', {'pending_orders': pending_orders})

@user_passes_test(is_admin, login_url='login')
@transaction.atomic
def admin_process_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if order.is_processed:
        messages.warning(request, "This order has already been processed.")
        return redirect('admin_order')

    if request.user.is_superuser:
        # Option A: Get the first seller profile available as a fallback
        seller_profile = Seller.objects.first() 
        
        # Option B: Or try to get a specific admin seller profile
        # seller_profile = Seller.objects.get_or_create(user=request.user, defaults={'store_name': 'Admin Store'})[0]
    else:
        # For regular sellers, keep the standard 404 behavior
        seller_profile = get_object_or_404(Seller, user=request.user)
    
    running_total = 0
    
    for item in order.items.all():
        product = item.product
        actual_qty = min(item.quantity, product.quantity)
        
        if actual_qty > 0:
            # 1. Update Inventory
            product.quantity = F('quantity') - actual_qty
            product.save()

            # 2. Update OrderItem fulfilled quantity
            item.quantity = actual_qty
            item.save()
            
            subtotal = actual_qty * item.price_at_purchase
            running_total += subtotal

            # 3. Create a record in the Sale table
            Sale.objects.create(
                seller=seller_profile,
                products=product,
                sale_amount=subtotal,
                # You can pull payment_method from a form or default to 'cash'
                payment_method='cash', 
                is_completed=True
            )
        else:
            item.quantity = 0
            item.save()

    # 4. Finalize Order
    order.total_amount = running_total
    order.is_processed = True
    order.status = 'Processed'
    order.save()

    messages.success(request, f"Order #{order.order_number} processed and Sales recorded.")
    return redirect('admin_receipt', order_number=order.order_number)

def admin_delete_order(request, order_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect('login')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order_num = order.order_number
        order.delete()
        messages.success(request, f"Order #{order_num} has been successfully deleted.")
    
    return redirect('admin_order') # Change this to your actual orders list view name

@user_passes_test(is_admin, login_url='login')
def admin_receipt(request, order_number):
    """
    Fetches the processed order and renders the receipt template.
    The template contains the auto-print JavaScript.
    """
    # We use order_number (the unique CharField) instead of ID for cleaner URLs
    # and better security/privacy.
    order = get_object_or_404(Order, order_number=order_number)
    
    # We don't need to fetch OrderItems separately because we used 
    # related_name='items' in the model. We can access them via order.items.all() 
    # directly in the template.
    
    return render(request, 'admin/admin_receipt.html', {
        'order': order,
    })

@user_passes_test(is_admin, login_url='login')
def clear_orders(request):
    if request.method == 'POST':
        count = Order.objects.count()
        Order.objects.all().delete()
        
        messages.success(request, f"Successfully cleared {count} orders from the database.")
        return redirect('admin_order')
    
    # If someone tries to access via GET, just send them back
    return redirect('admin_order')

@user_passes_test(is_admin, login_url='login')
def manage_credits(request):
    # Only admins or authorized staff should see this
    if not request.user.is_superuser:
        return redirect('seller_dashboard')
        
    credits = Credit.objects.all().order_by('-credit_date')
    return render(request, 'admin/manage_credits.html', {'credits': credits})

from django.views.decorators.http import require_POST

@require_POST
def delete_credit(request, credit_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect('manage_credits')
        
    credit = get_object_or_404(Credit, id=credit_id)
    
    # Safety Check: Only delete if the status is 'paid'
    if credit.status == 'paid':
        customer_name = credit.customer.first_name
        credit.delete()
        messages.success(request, f"Credit record for {customer_name} has been deleted.")
    else:
        messages.error(request, "Cannot delete an active or overdue credit.")
        
    return redirect('manage_credits')

from django.contrib import messages

def mark_credit_as_paid(request, credit_id):
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized access.")
        return redirect('manage_credits')
        
    credit = get_object_or_404(Credit, id=credit_id)
    
    if credit.status != 'paid':
        credit.status = 'paid'
        credit.save()
        messages.success(request, f"Credit for {credit.customer.first_name} marked as paid.")
    else:
        messages.info(request, "This credit is already settled.")
        
    return redirect('manage_credits')

from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from .models import Customer

def manage_customers(request):
    if not request.user.is_superuser:
        return redirect('seller_dashboard')

    # Optimization: Use the 'credits' related_name to sum the amounts
    customers = Customer.objects.annotate(
        total_debt=Coalesce(
            Sum('credits__amount', filter=Q(credits__status='active') | Q(credits__status='overdue')),
            0,
            output_field=DecimalField()
        )
    ).order_by('-total_debt', 'last_name')

    return render(request, 'admin/manage_customers.html', {'customers': customers})

def toggle_credit_eligibility(request, customer_id):
    if not request.user.is_superuser:
        return redirect('manage_customers')
        
    customer = get_object_or_404(Customer, id=customer_id)
    customer.is_eligible_for_credit = not customer.is_eligible_for_credit
    customer.save()
    return redirect('manage_customers')


#____________________SELLER SECTION_______________________

@login_required
def seller_dashboard(request):
    try:
        seller = request.user.seller
    except Seller.DoesNotExist:
        logout(request)
        messages.error(request, "Seller profile not found.")
        return redirect('login')
    # 1. Product Consultation (Filterable)
    search_query = request.GET.get('search', '')
    products = Product.objects.all().order_by('name')
    customers = Customer.objects.all().order_by('first_name')
    if search_query:
        products = products.filter(Q(name__icontains=search_query) | Q(category__name__icontains=search_query))

    # 2. Reporting Logic (Today vs Month)
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    daily_sales = Sale.objects.filter(seller=request.user.seller, sale_date__date=today, is_completed=True)
    monthly_sales = Sale.objects.filter(seller=request.user.seller, sale_date__date__gte=month_start, is_completed=True)

    # 3. Credits (is_completed=False logic)
    active_credits = Sale.objects.filter(seller=request.user.seller, is_completed=False).order_by('-sale_date')

    # Calculate total credit amount for this seller today
    total_credit_today = Credit.objects.filter(
        processed_by=seller,
        credit_date__date=today
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'products': products,
        'customers': customers,
        'today_total': daily_sales.aggregate(Sum('sale_amount'))['sale_amount__sum'] or 0,
        'month_total': monthly_sales.aggregate(Sum('sale_amount'))['sale_amount__sum'] or 0,
        'today_count': daily_sales.count(),
        'active_credits': active_credits,
        'low_stock': Product.objects.filter(quantity__lte=models.F('min_stock_level')),
        'total_credit_today': total_credit_today
    }
    return render(request, 'seller/seller_dashboard.html', context)

@transaction.atomic
def process_sale(request):
    try:
        seller = request.user.seller
    except Seller.DoesNotExist:
        logout(request)
        messages.error(request, "Seller profile not found.")
        return redirect('login')
    if request.method == "POST":
        product_ids = request.POST.getlist('product_ids')
        quantities = request.POST.getlist('quantities')
        is_completed = 'is_completed' in request.POST
        customer_id = request.POST.get('customer_id')
        
        total_sale_amount = 0
        products_to_credit = [] # To keep track of unique products for the Credit table

        for p_id, qty in zip(product_ids, quantities):
            product = get_object_or_404(Product, id=p_id)
            qty_int = int(qty)
            total_sale_amount += (product.selling_price * qty_int)
            products_to_credit.append(product)

            # Create individual sale records for reporting
            for _ in range(qty_int):
                Sale.objects.create(
                    seller=request.user.seller,
                    products=product,
                    sale_amount=product.selling_price,
                    is_completed=is_completed
                )
            
            # Deduct inventory
            product.quantity -= qty_int
            product.save()

        # Handle Credit logic
        if not is_completed:
            if not customer_id:
                messages.error(request, "Please select a customer for credit.")
                return redirect('seller_dashboard')

            # This will only succeed if the customer exists AND is marked as eligible
            customer = get_object_or_404(Customer, id=customer_id, is_eligible_for_credit=True)
            
            # 1. Create the Credit record
            new_credit = Credit.objects.create(
                customer=customer,
                amount=total_sale_amount,
                processed_by=request.user.seller,
                status='active'
            )
            
            # 2. Link the products (Bulk add)
            new_credit.products.add(*products_to_credit)
            
            messages.success(request, f"Credit of {total_sale_amount} XAF registered for {customer}.")
        
        return redirect('seller_dashboard')

from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Sale, Credit, Order, SalesReport # Ensure all are imported

def generate_daily_report(request):
    try:
        seller = request.user.seller
    except Seller.DoesNotExist:
        logout(request)
        messages.error(request, "Seller profile not found.")
        return redirect('login')

    today = timezone.now().date()
    
    # 1. Total Activity (All sales, including those on credit)
    all_sales_today = Sale.objects.filter(sale_date__date=today, seller=seller)
    
    if not all_sales_today.exists():
        messages.warning(request, "No sales recorded today to generate a report.")
        return redirect('seller_dashboard')

    # Aggregate Sales Data
    sales_summary = all_sales_today.aggregate(
        gross_revenue=Sum('sale_amount'),
        total_items=Count('id'),
        cash_total=Sum('sale_amount', filter=Q(payment_method='cash', is_completed=True)),
        momo_total=Sum('sale_amount', filter=Q(payment_method='mobile_money', is_completed=True))
    )

    # 2. Aggregate Credits (Debt issued today)
    credits_issued = Credit.objects.filter(
        credit_date__date=today, 
        processed_by=seller
    ).aggregate(total_debt=Sum('amount'))['total_debt'] or 0

    # 3. Aggregate Orders (Check for pending vs completed)
    orders_summary = Order.objects.filter(
        order_date__date=today
    ).aggregate(
        total_orders=Count('id'),
        pending_orders_val=Sum('total_amount', filter=Q(status='pending'))
    )

    # 4. Final Calculations
    total_sales_value = sales_summary['gross_revenue'] or 0
    actual_cash_collected = (sales_summary['cash_total'] or 0) + (sales_summary['momo_total'] or 0)
    
    # 5. Create or Update the SalesReport
    # Ensure your SalesReport model has these fields added to its definition
    report, created = SalesReport.objects.update_or_create(
        report_date=today,
        generated_by=seller,
        defaults={
            'total_sales': total_sales_value,
            'cash_sales': sales_summary['cash_total'] or 0,
            'mobile_money_sales': sales_summary['momo_total'] or 0,
            'credit_sales_total': credits_issued,
            'net_cash_collected': actual_cash_collected,
            'total_products_sold': sales_summary['total_items'] or 0,
            'orders_processed': orders_summary['total_orders'] or 0,
            'pending_order_value': orders_summary['pending_orders_val'] or 0,
        }
    )

    messages.success(request, f"Daily report for {today} synced. Cash in Hand: {actual_cash_collected} XAF")
    return redirect('sales_report_list')

def sales_report_list(request):
    try:
        seller = request.user.seller
    except Seller.DoesNotExist:
        logout(request)
        messages.error(request, "Seller profile not found.")
        return redirect('login')
    """
    Displays a history of all daily/monthly sales reports generated.
    """
    # Fetch reports for the logged-in seller, newest first
    reports = SalesReport.objects.filter(
        generated_by=request.user.seller
    ).order_by('-report_date')
    
    context = {
        'reports': reports,
        'page_title': 'My Sales Reports'
    }
    return render(request, 'seller/sales_report_list.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import logout
from django.contrib import messages
from .models import SalesReport, Seller

def print_sales_report(request, report_id):
    # 1. Determine Identity
    is_admin = request.user.is_superuser
    seller_profile = None

    if not is_admin:
        try:
            seller_profile = request.user.seller
        except (AttributeError, Seller.DoesNotExist):
            logout(request)
            messages.error(request, "Access denied. Seller profile not found.")
            return redirect('login')

    # 2. Fetch the report
    report = get_object_or_404(SalesReport, id=report_id)

    # 3. Permission Check
    # Match against 'generated_by' which we updated in the model earlier
    if not is_admin and report.generated_by != seller_profile:
        messages.error(request, "You do not have permission to view this report.")
        return redirect('seller_dashboard')

    # 4. Context for the Print Template
    # We include a 'calculated_variance' to help spot errors on the printed sheet
    context = {
        'report': report,
        'is_admin': is_admin,
        'generated_at': report.report_date,
        # Variance helps identify if (Cash + MoMo + Credit) matches Total Sales
        'variance': (report.cash_sales + report.mobile_money_sales + report.credit_sales_total) - report.total_sales
    }

    return render(request, 'seller/print_report.html', context)

def seller_dashboard_order(request):
    # Only show orders that haven't been processed yet
    pending_orders = Order.objects.filter(is_processed=False).order_by('-order_date')
    return render(request, 'seller/seller_dashboard_order.html', {'pending_orders': pending_orders})

@transaction.atomic
def process_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if order.is_processed:
        messages.warning(request, "This order has already been processed.")
        return redirect('seller_dashboard_order')

    # Identify the seller (current logged-in user)
    # Ensure your Seller model has a OneToOne relationship with User
    seller_profile = get_object_or_404(Seller, user=request.user)
    
    running_total = 0
    
    for item in order.items.all():
        product = item.product
        actual_qty = min(item.quantity, product.quantity)
        
        if actual_qty > 0:
            # 1. Update Inventory
            product.quantity = F('quantity') - actual_qty
            product.save()

            # 2. Update OrderItem fulfilled quantity
            item.quantity = actual_qty
            item.save()
            
            subtotal = actual_qty * item.price_at_purchase
            running_total += subtotal

            # 3. Create a record in the Sale table
            Sale.objects.create(
                seller=seller_profile,
                products=product,
                sale_amount=subtotal,
                # You can pull payment_method from a form or default to 'cash'
                payment_method='cash', 
                is_completed=True
            )
        else:
            item.quantity = 0
            item.save()

    # 4. Finalize Order
    order.total_amount = running_total
    order.is_processed = True
    order.status = 'Processed'
    order.save()

    messages.success(request, f"Order #{order.order_number} processed and Sales recorded.")
    return redirect('receipt', order_number=order.order_number)

def seller_delete_order(request, order_id):
    is_seller = hasattr(request.user, 'seller')
    
    if not (request.user.is_superuser or is_seller):
        messages.error(request, "Unauthorized access. Only sellers or admins can delete orders.")
        return redirect('login')

    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        order_num = order.order_number
        order.delete()
        messages.success(request, f"Order #{order_num} has been successfully deleted.")
    
    return redirect('seller_dashboard_order')

def receipt(request, order_number):
    """
    Fetches the processed order and renders the receipt template.
    The template contains the auto-print JavaScript.
    """
    # We use order_number (the unique CharField) instead of ID for cleaner URLs
    # and better security/privacy.
    order = get_object_or_404(Order, order_number=order_number)
    
    # We don't need to fetch OrderItems separately because we used 
    # related_name='items' in the model. We can access them via order.items.all() 
    # directly in the template.
    
    return render(request, 'seller/receipt.html', {
        'order': order,
    })

def check_for_new_orders(request):
    # Fetch orders created in the last 1 minute (adjust as needed)
    # Or filter by a 'status' field if you have one (e.g., status='Pending')
    new_orders = Order.objects.filter(status='Pending').order_by('-order_date')[:5]
    
    return render(request, 'partials/order_notification.html', {
        'new_orders': new_orders,
        'count': new_orders.count()
    })

'''from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Sale


def delete_all_sales(request):
    if request.method == "POST":
        # Filter to ensure the seller only deletes THEIR own sales
        my_sales = Sale.objects.filter(seller=request.user.seller)
        count = my_sales.count()
        
        if count > 0:
            my_sales.delete()
            messages.success(request, f"Successfully cleared {count} sales from your record.")
        else:
            messages.info(request, "There were no sales to delete.")
            
        return redirect('dashboard_home')'''

def shop_view(request):
    all_products = Product.objects.all()
    categories = Category.objects.all()
    
    # Optional: Add pagination logic here
    paginator = Paginator(all_products, 6) # 6 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'shop.html', {
        'products': page_obj,
        'categories': categories
    })

def seller_dashboard_order(request):
    # Only show orders that haven't been processed yet
    pending_orders = Order.objects.filter(is_processed=False).order_by('-order_date')
    return render(request, 'seller/seller_dashboard_order.html', {'pending_orders': pending_orders})

def seller_manage_credits(request):
    # Only admins or authorized staff should see this
        
    credits = Credit.objects.all().order_by('-credit_date')
    return render(request, 'seller/seller_manage_credits.html', {'credits': credits})

#___________________CHATBOT SECTION_______________________

# Initialize client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    
)

load_dotenv()
def chatbot_response(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message")

            products = Product.objects.all()[:20] 
            inventory_summary = "\n".join([
                f"- {p.name}: {p.selling_price} XAF (Stock: {p.quantity} {p.unit})" 
                for p in products
            ])

            system_prompt = f"""
            You are the official AI Assistant for our Mini Market called Momshop. 
            Your theme colors are Orange, White, and Dull Black.

            SHOP FACTS:
            - Location: Makepe St. Tropez, Douala.
            - Hours: 8 AM - 10 PM.
            - Payments: Cash, Orange Money, Mobile Money.
            - Delivery: 1,000 XAF within the city.

            INVENTORY:
            {inventory_summary}

            STRICT INSTRUCTIONS:
            - If a customer asks about a product, check the inventory list above.
            - If you DO NOT know the answer, or if the question is about a specific complaint, 
              refund, or a product NOT in the list, reply: 
              "I'm sorry, I don't have that specific information. Please contact our 
              Human Support team directly at +237 600 000 000 for further assistance."
            - Keep answers helpful and concise.
            """

            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:8000", # Required for OpenRouter
                },
                model="nex-agi/deepseek-v3.1-nex-n1:free",
                messages=[
                   {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            
            bot_reply = completion.choices[0].message.content
            return JsonResponse({"reply": bot_reply})

        except Exception as e:
            # THIS WILL PRINT THE EXACT ERROR IN THE CHAT WINDOW
            return JsonResponse({"reply": f"Backend Error: {str(e)}"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


def custom_404(request, exception):
    return render(request, '404.html', status=404)    

def error_500(request):
    return render(request, '500.html', status=500)