from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from .models import Customer, Product, Expenses, Supplier
import os

class CustomerRegistrationForm(forms.ModelForm):
    # User account fields
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        }),
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        min_length=8,
        help_text="Password must be at least 8 characters long."
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    # Cameroon phone number validator
    phone_regex = RegexValidator(
        regex=r'^(\+237|237)?[6-9]\d{8}$',
        message="Phone number must be entered in the format: '+2376XXXXXXXX' or '6XXXXXXXX'. Up to 9 digits allowed."
    )
    
    # Customer fields
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        validators=[phone_regex],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '6XX XXX XXX or +2376XX XXX XXX'
        }),
        help_text="Enter your Cameroonian phone number"
    )
    
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your complete address'
        })
    )
    
    # Common Cameroonian cities
    CAMEROON_CITIES = [
        ('', 'Select City'),
        ('Douala', 'Douala'),
        ('Yaoundé', 'Yaoundé'),
        ('Bamenda', 'Bamenda'),
        ('Bafoussam', 'Bafoussam'),
        ('Garoua', 'Garoua'),
        ('Maroua', 'Maroua'),
        ('Ngaoundéré', 'Ngaoundéré'),
        ('Kumba', 'Kumba'),
        ('Limbe', 'Limbe'),
        ('Buea', 'Buea'),
        ('Ebolowa', 'Ebolowa'),
        ('Bertoua', 'Bertoua'),
    ]
    
    city = forms.ChoiceField(
        choices=CAMEROON_CITIES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    CUSTOMER_TYPES = [
        ('regular', 'Regular Customer'),
        ('occasional', 'Occasional Customer'),
        ('wholesale', 'Wholesale Customer'),
    ]
    
    customer_type = forms.ChoiceField(
        choices=CUSTOMER_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        initial='occasional'
    )

    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'phone', 'email', 
            'address', 'city', 'customer_type'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        # Check if username already exists
        username = cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        
        # Check if phone number already exists
        phone = cleaned_data.get("phone")
        if Customer.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Phone number already registered")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Create User first
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name']
        )
        
        # Create Customer profile
        customer = super().save(commit=False)
        customer.user = user
        
        if commit:
            customer.save()
        
        return customer
    
# app_name/forms.py
from django import forms
from .models import Product, Seller, Expenses, Customer, Supplier, Category
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

# --- 1. Management Forms ---

class ProductForm(forms.ModelForm):
    category_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Beverages, Electronics, Clothing'
        }),
        help_text="Enter category name (will be created if it doesn't exist)"
    )
    
    supplier_name = forms.CharField(
        max_length=200,
        required=False,  # Make supplier optional
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Coca-Cola Company, Local Supplier'
        }),
        help_text="Enter supplier name (optional, will be created if it doesn't exist)"
    )
    
    supplier_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Supplier phone number'
        })
    )

    class Meta:
        model = Product
        # Include all fields the admin needs to manage
        fields = ['name', 'description', 'buying_price', 'selling_price', 'unit', 'quantity', 'min_stock_level', 'image']
        # Apply Bootstrap's 'form-control' class for styling
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'buying_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'  # Accept only image files
            }),
        }
        help_texts = {
            'image': 'Upload a product image (JPEG, PNG, GIF) - Max 5MB',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for category and supplier if editing existing product
        if self.instance and self.instance.pk:
            if self.instance.category:
                self.fields['category_name'].initial = self.instance.category.name
            if self.instance.supplier:
                self.fields['supplier_name'].initial = self.instance.supplier.name
                self.fields['supplier_phone'].initial = self.instance.supplier.phone
        
        # Add initial stock field for new products
        if not self.instance.pk:
            self.fields['initial_stock'] = forms.IntegerField(
                required=False,
                initial=0,
                min_value=0,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Initial stock quantity'
                }),
                help_text="Initial stock quantity (optional)"
            ) 
    
    def clean_category_name(self):
        category_name = self.cleaned_data.get('category_name', '').strip()
        if not category_name:
            raise ValidationError("Category name is required.")
        return category_name
    
    def clean_supplier_name(self):
        supplier_name = self.cleaned_data.get('supplier_name', '').strip()
        if not supplier_name:
            raise ValidationError("Supplier name is required, If there is no supplier just put 0 please. Thank you.")
        supplier_phone = self.cleaned_data.get('supplier_phone', '').strip()
        if supplier_phone and not supplier_name:
            raise ValidationError("Supplier name is required when phone number is provided.")
        return supplier_name
    
    def clean(self):
        cleaned_data = super().clean()
        buying_price = cleaned_data.get('buying_price')
        selling_price = cleaned_data.get('selling_price')
        
        # Validate pricing
        if buying_price and selling_price:
            if selling_price <= buying_price:
                raise ValidationError("Selling price must be higher than buying price for profitability.")
        
        # Validate barcode uniqueness
        barcode = cleaned_data.get('barcode')
        if barcode:
            existing_product = Product.objects.filter(barcode=barcode)
            if self.instance.pk:
                existing_product = existing_product.exclude(pk=self.instance.pk)
            
            if existing_product.exists():
                raise forms.ValidationError(f"A product with barcode '{barcode}' already exists.")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Get or create category
        category_name = self.cleaned_data.get('category_name', '').strip()
        if category_name:
            category, created = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Category for {self.cleaned_data["name"]}'}
            )
            self.instance.category = category
        
        # Get or create supplier if name is provided
        supplier_name = self.cleaned_data.get('supplier_name', '').strip()
        supplier_phone = self.cleaned_data.get('supplier_phone', '').strip()
        if supplier_name:
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_name,
                defaults={
                    'phone': supplier_phone,
                    'contact_person': 'Not specified',
                    'address': 'Address not provided',
                    'city': 'Douala'
                }
            )
            self.instance.supplier = supplier
        else:
            # Clear supplier if no name provided
            self.instance.supplier = None
        
        return super().save(commit)     

class ExpensesForm(forms.ModelForm):
    class Meta:
        model = Expenses
        fields = ['expenses_type', 'description', 'amount', 'expenses_date']
        widgets = {
            'expenses_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'expenses_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class SellerForm(forms.ModelForm):
    # User account fields
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        min_length=8,
        help_text="Password must be at least 8 characters long."
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )

    class Meta:
        model = Seller
        fields = [
            'phone', 'address', 'id_card_number', 'salary', 'hire_date'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Complete address'
            }),
            'id_card_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CNI Number'
            }),
            'salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Monthly salary'
            }),
            'hire_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }   
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        # Check if username already exists
        username = cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already exists")
        
        # Check if email already exists
        email = cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered")
        
        return cleaned_data

class SellerUpdateForm(forms.ModelForm):
    # User fields
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control'
        })
    )
    
    first_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )
    
    last_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = Seller
        fields = [
            'phone', 'address', 'id_card_number', 'salary', 'hire_date', 'is_active'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'id_card_number': forms.TextInput(attrs={'class': 'form-control'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
    
    def save(self, commit=True):
        seller = super().save(commit=False)
        
        # Update associated User
        if seller.user:
            seller.user.email = self.cleaned_data['email']
            seller.user.first_name = self.cleaned_data['first_name']
            seller.user.last_name = self.cleaned_data['last_name']
            seller.user.save()
        
        if commit:
            seller.save()
        
        return seller          
    
class ExpensesForm(forms.ModelForm):
    class Meta:
        model = Expenses
        fields = ['expenses_number','expenses_type', 'description', 'amount', 'expenses_date']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'expenses_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'receipt_number': forms.TextInput(attrs={'class': 'form-control'}),
        }    