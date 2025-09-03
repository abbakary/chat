from django import forms
from django.contrib.auth.models import User, Group
from .models import Customer, Order, Vehicle, InventoryItem

class CustomerEditForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "full_name","phone","email","address","notes",
            "customer_type","organization_name","tax_number","personal_subtype","current_status",
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+256 XXX XXX XXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Additional notes'}),
            'customer_type': forms.Select(attrs={'class': 'form-select'}),
            'organization_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Organization name'}),
            'tax_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tax number/TIN'}),
            'personal_subtype': forms.Select(attrs={'class': 'form-select'}),
            'current_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()
        t = cleaned.get("customer_type")
        if t in {"government","ngo","company"}:
            if not cleaned.get("organization_name"):
                self.add_error("organization_name","Required for organizational customers")
            if not cleaned.get("tax_number"):
                self.add_error("tax_number","Required for organizational customers")
        elif t == "personal":
            if not cleaned.get("personal_subtype"):
                self.add_error("personal_subtype","Please specify if you are the owner or driver")
        return cleaned

class CustomerBasicForm(forms.Form):
    """Step 1: Basic customer information - used for quick customer creation"""
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter customer full name',
            'required': True
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+256 XXX XXX XXX',
            'required': True
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com (optional)'
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter customer address (optional)'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes (optional)'
        })
    )

class CustomerStep1Form(forms.Form):
    """Step 1: Basic customer information"""
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter full name',
            'required': True
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+256 XXX XXX XXX',
            'required': True
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@example.com'
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter address'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional notes'
        })
    )

class CustomerStep2Form(forms.Form):
    """Step 2: Service intent"""
    INTENT_CHOICES = [
        ("service", "I need a service"),
        ("sales", "I want to buy something"),
        ("inquiry", "Just an inquiry")
    ]
    
    intent = forms.ChoiceField(
        choices=INTENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

class CustomerStep3Form(forms.Form):
    """Step 3: Service/Sales type"""
    SERVICE_TYPE_CHOICES = [
        ("oil_change", "Oil Change"),
        ("engine_diagnostics", "Engine Diagnostics"),
        ("brake_repair", "Brake Repair"),
        ("tire_rotation", "Tire Rotation"),
        ("wheel_alignment", "Wheel Alignment"),
        ("battery_check", "Battery Check"),
        ("fluid_top_up", "Fluid Top-Up"),
        ("general_maintenance", "General Maintenance"),
        ("other", "Other Service")
    ]

    SALES_TYPE_CHOICES = [
        ("tire_sales", "Tire Sales"),
        ("parts_sales", "Auto Parts"),
        ("oil_sales", "Oil & Fluids"),
        ("battery_sales", "Battery"),
        ("accessories", "Accessories"),
        ("other", "Other Products")
    ]

    # Allow multiple service selections via checkboxes
    service_type = forms.MultipleChoiceField(
        choices=SERVICE_TYPE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    sales_type = forms.ChoiceField(
        choices=SALES_TYPE_CHOICES,
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

class CustomerStep4Form(forms.Form):
    """Step 4: Customer type and organizational details"""
    customer_type = forms.ChoiceField(
        choices=Customer.TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select', 'required': True})
    )
    organization_name = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Organization/Company name'
        })
    )
    tax_number = forms.CharField(
        required=False,
        max_length=64,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tax number/TIN'
        })
    )
    personal_subtype = forms.ChoiceField(
        choices=[('', 'Select...')] + Customer.PERSONAL_SUBTYPE,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned = super().clean()
        customer_type = cleaned.get('customer_type')
        
        if customer_type in ['government', 'ngo', 'company']:
            if not cleaned.get('organization_name'):
                self.add_error('organization_name', 'Organization name is required for this customer type')
            if not cleaned.get('tax_number'):
                self.add_error('tax_number', 'Tax number is required for this customer type')
        elif customer_type == 'personal':
            if not cleaned.get('personal_subtype'):
                self.add_error('personal_subtype', 'Please specify if you are the owner or driver')
        
        return cleaned

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["plate_number", "make", "model", "vehicle_type"]
        widgets = {
            'plate_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., UAH 123A',
                'style': 'text-transform: uppercase;'
            }),
            'make': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Toyota, Honda'
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Camry, Civic'
            }),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('', 'Select vehicle type'),
                ('sedan', 'Sedan'),
                ('suv', 'SUV'),
                ('truck', 'Truck'),
                ('van', 'Van'),
                ('motorcycle', 'Motorcycle'),
                ('bus', 'Bus'),
                ('other', 'Other')
            ])
        }

class OrderForm(forms.ModelForm):
    SERVICE_OPTIONS = [
        ("oil_change", "Oil Change"),
        ("engine_diagnostics", "Engine Diagnostics"),
        ("brake_repair", "Brake Repair"),
        ("tire_rotation", "Tire Rotation"),
        ("wheel_alignment", "Wheel Alignment"),
        ("battery_check", "Battery Check"),
        ("fluid_top_up", "Fluid Top-Up"),
        ("general_maintenance", "General Maintenance"),
    ]

    service_selection = forms.MultipleChoiceField(
        choices=SERVICE_OPTIONS, 
        required=False, 
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Order
        fields = [
            "type",
            "vehicle",
            "priority",
            "description",
            "estimated_duration",
            "item_name",
            "brand",
            "quantity",
            "tire_type",
            "inquiry_type",
            "questions",
            "contact_preference",
            "follow_up_date",
        ]
        widgets = {
            "type": forms.Select(attrs={'class': 'form-select'}),
            "vehicle": forms.Select(attrs={'class': 'form-select'}),
            "priority": forms.Select(attrs={'class': 'form-select'}),
            "description": forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe the issue or service needed'}),
            "estimated_duration": forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            "item_name": forms.Select(attrs={'class': 'form-select'}),
            "brand": forms.Select(attrs={'class': 'form-select'}),
            "quantity": forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            "tire_type": forms.Select(attrs={'class': 'form-select'}),
            "inquiry_type": forms.Select(attrs={'class': 'form-select'}),
            "questions": forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            "contact_preference": forms.Select(attrs={'class': 'form-select'}),
            "follow_up_date": forms.DateInput(attrs={"type": "date", 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Default estimated duration for service orders
        if not self.fields["estimated_duration"].initial:
            self.fields["estimated_duration"].initial = 50

        # Dynamic item and brand choices from inventory
        try:
            names = list(InventoryItem.objects.values_list('name', flat=True).order_by('name').distinct())
            name_choices = [('', 'Select item')] + [(n, n) for n in names if n]
        except Exception:
            name_choices = [('', 'Select item')]
        self.fields["item_name"].widget = forms.Select(attrs={'class': 'form-select'}, choices=name_choices)

        try:
            brands = list(InventoryItem.objects.exclude(brand__isnull=True).exclude(brand='').values_list('brand', flat=True).order_by('brand').distinct())
            brand_choices = [('', 'Select brand')] + [(b, b) for b in brands if b]
        except Exception:
            brand_choices = [('', 'Select brand')]
        self.fields["brand"].widget = forms.Select(attrs={'class': 'form-select'}, choices=brand_choices)
        
        # Tire type choices
        self.fields["tire_type"].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[
                ('', 'Select condition'),
                ("New", "New"),
                ("Used", "Used"),
                ("Refurbished", "Refurbished")
            ]
        )
        
        # Inquiry type choices
        self.fields["inquiry_type"].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[
                ('', 'Select inquiry type'),
                ("Pricing", "Pricing"),
                ("Services", "Services"),
                ("Appointment Booking", "Appointment Booking"),
                ("General", "General")
            ]
        )
        
        # Contact preference choices
        self.fields["contact_preference"].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[
                ('', 'Select preference'),
                ("phone", "Phone"),
                ("email", "Email"),
                ("whatsapp", "WhatsApp")
            ]
        )

    def clean(self):
        cleaned = super().clean()
        t = cleaned.get("type")
        
        if t == "sales":
            for f in ["item_name", "brand"]:
                if not cleaned.get(f):
                    self.add_error(f, "Required for Sales orders")
            q = cleaned.get("quantity")
            if not q or q < 1:
                self.add_error("quantity", "Quantity must be at least 1")
                
        elif t == "service":
            if not cleaned.get("description"):
                self.add_error("description", "Problem description required for Service orders")
            if not cleaned.get("estimated_duration"):
                self.add_error("estimated_duration", "Estimated duration required for Service orders")
            services = cleaned.get("service_selection") or []
            if services:
                desc = cleaned.get("description") or ""
                desc_services = "\nSelected services: " + ", ".join(dict(self.SERVICE_OPTIONS)[s] for s in services)
                cleaned["description"] = (desc + desc_services).strip()
                
        elif t == "consultation":
            if not cleaned.get("inquiry_type"):
                self.add_error("inquiry_type", "Inquiry type is required")
            if not cleaned.get("questions"):
                self.add_error("questions", "Please provide your questions")
                
        return cleaned

class CustomerSearchForm(forms.Form):
    """Form for searching existing customers"""
    search_query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, phone, email, or customer code...',
            'id': 'customer-search'
        })
    )

class InquiryResponseForm(forms.Form):
    """Form for responding to customer inquiries"""
    response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter your response to the customer...'
        })
    )
    
    follow_up_required = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    follow_up_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ["name", "brand", "quantity", "price"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
        }

class AdminUserForm(forms.ModelForm):
    group_manager = forms.BooleanField(
        required=False, 
        label="Manager role",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active", "is_staff"]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            mgr, _ = Group.objects.get_or_create(name="manager")
            self.fields["group_manager"].initial = mgr in self.instance.groups.all()

    def save(self, commit=True):
        user = super().save(commit)
        if user.pk:
            mgr, _ = Group.objects.get_or_create(name="manager")
            if self.cleaned_data.get("group_manager"):
                user.groups.add(mgr)
            else:
                user.groups.remove(mgr)
            if commit:
                user.save()
        return user

class SystemSettingsForm(forms.Form):
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company/Workshop name'})
    )
    default_priority = forms.ChoiceField(
        choices=[('low','Low'),('medium','Medium'),('high','High'),('urgent','Urgent')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    enable_unbranded_alias = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    allow_order_without_vehicle = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    sms_provider = forms.ChoiceField(
        choices=[('none','None'),('zapier','Zapier Webhook'),('twilio','Twilio')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
