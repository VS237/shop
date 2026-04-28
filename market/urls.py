from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
  path('', views.home, name='home'),
  path('shop/', views.shop, name='shop'),
  path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
  path('cart/', views.cart, name='cart'),
  path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
  path('cart/update/<int:product_id>/', views.update_cart, name='update_cart'),
  path('get-cart-count/', views.get_cart_count, name='get_cart_count'),
  path('place-order/', views.place_order, name='place_order'),
  path('receipt/<str:order_number>/', views.print_receipt, name='print_receipt'),
  path('order-success/<str:order_number>/', views.order_success, name='order_success'),
  path('contact/', views.contact, name='contact'),
  path('about/', views.about, name='about'),
  path('product_details/<int:pk>/', views.product_details, name='product_details'),
  path('profile/', views.profile, name='profile'),
  path('my-account/', views.my_credit_dashboard, name='customer_dashboard'),
  path('register/', views.user_register, name='register'),
  path('verify/', views.verify_code_view, name='verify_code'),
  path('resend-otp/', views.resend_otp, name='resend_otp'),
  path('forgot-password/', views.forgot_password, name='forgot_password'),
  path('update-password/', views.update_password, name='update_password'),
  path('password-reset/done/', views.password_reset_complete, name='password_reset_complete'),
  path('login/', views.user_login, name='login'),
  path('logout/', views.logout_view, name='logout'),

  #admin_dashboard
  path('dashboard/', views.dashboard_home, name='dashboard_home'),
  path('dashboard/products/', views.manage_products, name='manage_products'),
  path('products/add/', views.add_product, name='add_product'), 
  path('products/delete/<int:product_id>', views.product_delete, name='product_delete'), 
  path('product/edit/<int:product_id>/', views.add_product, name='edit_product'),
  path('sales/delete-all/', views.delete_all_sales, name='delete_all_sales'),
  path('reports/delete-all/', views.delete_all_reports, name='delete_all_reports'),
  path('dashboard/sellers/', views.manage_sellers, name='manage_sellers'),
  path('dashboard/sellers/create/', views.create_sellers, name='create_sellers'),
  path('dashboard/sellers/edit/<int:seller_id>', views.edit_sellers, name='edit_sellers'),
  path('dashboard/sellers/report/<int:seller_id>/', views.seller_sales_report, name='seller_sales_report'),
  path('dashboard/expenses/', views.manage_expenses, name='manage_expenses'),
  path('dashboard/expenses/delete/<int:expenses_id>/', views.delete_expenses, name='delete_expenses'),
  path('dashboard/sales/report/', views.sales_report, name='sales_report'),
  path('dashboard/order/', views.admin_order, name='admin_order'),
  path('dashboard/order/process/<int:order_id>/', views.admin_process_order, name='admin_process_order'),
  path('dashboard/order/delete/<int:order_id>/', views.admin_delete_order, name='admin_delete_order'),
  path('dashboard/<str:order_number>/print/', views.admin_receipt, name='admin_receipt'),
  path('dashboard/credits/', views.manage_credits, name='manage_credits'),
  path('dashboard/credits/delete/<int:credit_id>/', views.delete_credit, name='delete_credit'),
  path('dashboard/credits/mark-paid/<int:credit_id>/', views.mark_credit_as_paid, name='mark_credit_as_paid'),
  path('dashboard/customer/toggle-credit/<int:customer_id>/', views.toggle_credit_eligibility, name='toggle_credit_eligibility'),
  path('dashboard/customers/', views.manage_customers, name='manage_customers'),


  #sellerdashboard
  path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
  path('seller/process_sale/', views.process_sale, name='process_sale'),
  path('seller/report/', views.generate_daily_report, name='generate_daily_report'),
  path('my-reports/', views.sales_report_list, name='sales_report_list'),
  path('reports/print/<int:report_id>/', views.print_sales_report, name='print_sales_report'),
  path('dashboard/seller/order/', views.seller_dashboard_order, name='seller_dashboard_order'),
  path('process/<int:order_id>/', views.process_order, name='process_order'),
  path('dashboard/seller/order/delete/<int:order_id>/', views.seller_delete_order, name='seller_delete_order'),
  path('process/<str:order_number>/print', views.receipt, name='receipt'),
  path('seller/clear-orders/', views.clear_orders, name='clear_orders'),
  path('check-new-orders/', views.check_for_new_orders, name='check_for_new_orders'),
  path('manage-credits/', views.seller_manage_credits, name='seller_manage_credits'),
  
  
  #path('seller/pos-system/', views.pos_system, name='pos_system'),
  #path('seller/process-sale/', views.process_sale, name='process_sale'),
  #path('seller/receipt/<int:sale_id>/', views.sale_receipt, name='sale_receipt'),

  path('dashboard/sellers/toggle-status/<int:seller_id>/', views.toggle_seller_status, name='toggle_seller_status'),

  path('chatbot-response/', views.chatbot_response, name='chatbot_response'),

  
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler500 = 'market.views.error_500'
handler404 = 'market.views.custom_404'    