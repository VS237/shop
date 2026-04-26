from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from uuid import uuid4
from cloudinary.models import CloudinaryField
from django.utils import timezone
from datetime import timedelta

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class Customer(BaseModel):
    CUSTOMER_TYPES = [
        ('regular', 'Regular Customer'),
        ('occasional', 'Occasional Customer'),
        ('wholesale', 'Wholesale Customer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, default="Douala")
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='occasional')
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_eligible_for_credit = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
class DeliveryAgent(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    id_card_image = models.ImageField(upload_to='images/')
    phone = models.CharField(max_length=20)
    address = models.TextField()
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    vehicle_type = models.CharField(max_length=100)
    vehicle_plate = models.CharField(max_length=20)
    hire_date = models.DateField()
    
    def __str__(self):
        return f"Delivery: {self.user.get_full_name()}"    
    
class Seller(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    address = models.TextField()
    id_card_number = models.CharField(max_length=50, null=True, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Seller: {self.user.get_full_name()}"  
    
class Supplier(BaseModel):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, default="Douala")  # Common Cameroonian city
    payment_terms = models.TextField(blank=True)
    
    def __str__(self):
        return self.name    

class Category(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name          
    
class Product(BaseModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit = models.CharField(max_length=50)  # kg, piece, liter, etc.
    quantity=models.IntegerField(default=0)
    min_stock_level = models.IntegerField(default=10)
    image = CloudinaryField('image') # Replaces models.ImageField
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    
    def __str__(self):
        return self.name

class Sale(BaseModel):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
    ]
    
    sale_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    products = models.ForeignKey(Product, on_delete=models.CASCADE)
    sale_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    sale_date = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Sale {self.sale_number}"

class Order(models.Model):
    # This stores the "Header" - info common to all items
    order_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2) # NEW FIELD
    city = models.CharField(max_length=100)
    town = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Pending') # Pending, Processed, Shipped
    is_processed = models.BooleanField(default=False)

class OrderItem(models.Model):
    # This stores the "Details" - the specific products
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

class Credit(BaseModel):
    CREDIT_STATUS = [
        ('active', 'Active Credit'),
        ('paid', 'Fully Paid'),
        ('overdue', 'Overdue'),
    ]
    
    credit_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="credits")
    
    # NEW: Link to multiple products
    products = models.ManyToManyField(Product, related_name="credit_items")
    
    # The total monetary value of the debt
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    credit_date = models.DateTimeField(auto_now_add=True) 
    expected_return_date = models.DateField(default=timezone.now().date() + timedelta(days=30))
    status = models.CharField(max_length=20, choices=CREDIT_STATUS, default='active')
    processed_by = models.ForeignKey(Seller, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Credit {self.credit_number} - {self.customer.first_name} ({self.amount} XAF)"
    
class Expenses(BaseModel):
    EXPENSES_TYPES = [
        ('transport', 'Transport Cost'),
        ('electricity', 'Electricity Bill'),
        ('rent', 'Rent'),
        ('salary', 'Salaries'),
        ('maintenance', 'Maintenance'),
        ('other', 'Other'),
    ]
    
    expenses_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    expenses_type = models.CharField(max_length=20, choices=EXPENSES_TYPES)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    expenses_date = models.DateField()
    
    def __str__(self):
        return f"Expense {self.expenditure_number}"    
    
class Delivery(BaseModel):
    DELIVERY_STATUS = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    delivery_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    delivery_agent = models.ForeignKey(DeliveryAgent, on_delete=models.CASCADE)
    customer_address = models.ForeignKey(Customer, on_delete=models.CASCADE)
    delivery_date = models.DateField()
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='pending')
    delivery_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Delivery {self.delivery_number}"   

class Payment(BaseModel):
    PAYMENT_TYPES = [
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    reference_number = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(Seller, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Payment {self.reference_number}"  

class SalesReport(BaseModel):
    report_date = models.DateField(unique=True)
    credit_sales_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_cash_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    orders_processed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_customers = models.IntegerField(default=0)
    total_products_sold = models.IntegerField(default=0)
    cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mobile_money_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_order_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_by = models.ForeignKey(Seller, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Sales Report {self.report_date}"     

class Messages(BaseModel):
    description=models.TextField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    delivery_agent=models.ForeignKey(DeliveryAgent, on_delete=models.CASCADE)
    customer=models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return f"Messages {self.last_name}"      