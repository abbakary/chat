from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Customer(models.Model):
    TYPE_CHOICES = [
        ("government", "Government"),
        ("ngo", "NGO"),
        ("company", "Private Company"),
        ("personal", "Personal"),
        ("bodaboda", "Bodaboda"),
    ]
    PERSONAL_SUBTYPE = [("owner", "Owner"), ("driver", "Driver")]
    STATUS_CHOICES = [
        ("arrived", "Arrived"),
        ("in_service", "In Service"),
        ("completed", "Completed"),
        ("departed", "Departed"),
    ]

    code = models.CharField(max_length=32, unique=True, editable=False)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    customer_type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True)
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    tax_number = models.CharField(max_length=64, blank=True, null=True)
    personal_subtype = models.CharField(max_length=16, choices=PERSONAL_SUBTYPE, blank=True, null=True)

    registration_date = models.DateTimeField(default=timezone.now)
    arrival_time = models.DateTimeField(blank=True, null=True)
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="arrived")

    total_visits = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_visit = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.code:
            import uuid
            self.code = f"CUST{str(uuid.uuid4())[:8].upper()}"
            # Ensure uniqueness
            while Customer.objects.filter(code=self.code).exists():
                self.code = f"CUST{str(uuid.uuid4())[:8].upper()}"
        if not self.arrival_time:
            self.arrival_time = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.code})"

    class Meta:
        indexes = [
            models.Index(fields=["full_name"], name="idx_cust_name"),
            models.Index(fields=["phone"], name="idx_cust_phone"),
            models.Index(fields=["email"], name="idx_cust_email"),
            models.Index(fields=["registration_date"], name="idx_cust_reg"),
            models.Index(fields=["last_visit"], name="idx_cust_lastvisit"),
            models.Index(fields=["customer_type"], name="idx_cust_type"),
        ]


class Vehicle(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=32)
    make = models.CharField(max_length=64, blank=True, null=True)
    model = models.CharField(max_length=64, blank=True, null=True)
    vehicle_type = models.CharField(max_length=64, blank=True, null=True)

    def __str__(self):
        return f"{self.plate_number} - {self.make or ''} {self.model or ''}"

    class Meta:
        indexes = [
            models.Index(fields=["customer"], name="idx_vehicle_customer"),
            models.Index(fields=["plate_number"], name="idx_vehicle_plate"),
        ]


class Order(models.Model):
    TYPE_CHOICES = [("service", "Service"), ("sales", "Sales"), ("consultation", "Consultation")]
    STATUS_CHOICES = [
        ("created", "Created"),
        ("assigned", "Assigned"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PRIORITY_CHOICES = [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")]

    order_number = models.CharField(max_length=32, unique=True, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="created")
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default="medium")

    description = models.TextField(blank=True, null=True)
    estimated_duration = models.PositiveIntegerField(blank=True, null=True, help_text="Minutes")
    actual_duration = models.PositiveIntegerField(blank=True, null=True)

    # Sales fields
    item_name = models.CharField(max_length=64, blank=True, null=True)
    brand = models.CharField(max_length=64, blank=True, null=True)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    tire_type = models.CharField(max_length=32, blank=True, null=True)

    # Consultation fields
    inquiry_type = models.CharField(max_length=64, blank=True, null=True)
    questions = models.TextField(blank=True, null=True)
    contact_preference = models.CharField(max_length=16, blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)

    # Timestamps and assignment
    created_at = models.DateTimeField(default=timezone.now)
    assigned_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_orders")

    def save(self, *args, **kwargs):
        creating = self._state.adding
        if not self.order_number:
            import uuid
            self.order_number = f"ORD{str(uuid.uuid4())[:8].upper()}"
            # Ensure uniqueness
            while Order.objects.filter(order_number=self.order_number).exists():
                self.order_number = f"ORD{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)
        if creating:
            # Update visit tracking
            self.customer.total_visits = (self.customer.total_visits or 0) + 1
            self.customer.last_visit = timezone.now()
            self.customer.save()

    def __str__(self):
        return f"{self.order_number} - {self.customer.full_name}"

    class Meta:
        indexes = [
            models.Index(fields=["status"], name="idx_order_status"),
            models.Index(fields=["type"], name="idx_order_type"),
            models.Index(fields=["priority"], name="idx_order_priority"),
            models.Index(fields=["created_at"], name="idx_order_created"),
            models.Index(fields=["completed_at"], name="idx_order_completed"),
            models.Index(fields=["customer", "created_at"], name="idx_order_cust_created"),
            models.Index(fields=["type", "status"], name="idx_order_type_status"),
        ]


class InventoryItem(models.Model):
    name = models.CharField(max_length=128)
    brand = models.CharField(max_length=64, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.brand or ''})"

    class Meta:
        indexes = [
            models.Index(fields=["name"], name="idx_item_name"),
            models.Index(fields=["brand"], name="idx_item_brand"),
            models.Index(fields=["name", "brand"], name="idx_item_name_brand"),
            models.Index(fields=["created_at"], name="idx_item_created"),
        ]
