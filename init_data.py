#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_tracker.settings')
django.setup()

from django.contrib.auth import get_user_model
from tracker.models import Customer, Order, Vehicle, InventoryItem
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

def create_admin_user():
    """Create admin user if it doesn't exist"""
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✓ Admin user created: username='admin', password='admin123'")
    else:
        print("✓ Admin user already exists")

def create_sample_data():
    """Create sample customers and orders"""
    # Create sample customers
    customers_data = [
        {'full_name': 'John Doe', 'phone': '+256701234567', 'email': 'john@example.com', 'customer_type': 'personal'},
        {'full_name': 'Jane Smith', 'phone': '+256702345678', 'email': 'jane@example.com', 'customer_type': 'personal'},
        {'full_name': 'Robert Johnson', 'phone': '+256703456789', 'email': 'robert@example.com', 'customer_type': 'personal'},
        {'full_name': 'Emily Davis', 'phone': '+256704567890', 'email': 'emily@example.com', 'customer_type': 'personal'},
        {'full_name': 'Michael Brown', 'phone': '+256705678901', 'email': 'michael@example.com', 'customer_type': 'personal'},
        {'full_name': 'ABC Company Ltd', 'phone': '+256706789012', 'email': 'info@abc.com', 'customer_type': 'company', 'organization_name': 'ABC Company Ltd', 'tax_number': 'TIN12345'},
    ]

    customers = []
    for data in customers_data:
        customer, created = Customer.objects.get_or_create(
            phone=data['phone'],
            defaults=data
        )
        if created:
            customers.append(customer)
            print(f"✓ Created customer: {customer.full_name}")

    # Create sample vehicles
    vehicles_data = [
        {'plate_number': 'UAH 123A', 'make': 'Toyota', 'model': 'Camry', 'vehicle_type': 'Sedan'},
        {'plate_number': 'UBA 456B', 'make': 'Honda', 'model': 'Civic', 'vehicle_type': 'Sedan'},
        {'plate_number': 'UBB 789C', 'make': 'Ford', 'model': 'F-150', 'vehicle_type': 'Truck'},
        {'plate_number': 'UBC 012D', 'make': 'BMW', 'model': 'X5', 'vehicle_type': 'SUV'},
        {'plate_number': 'UBD 345E', 'make': 'Mercedes', 'model': 'C-Class', 'vehicle_type': 'Sedan'},
    ]

    for i, vehicle_data in enumerate(vehicles_data):
        if i < len(customers):
            vehicle, created = Vehicle.objects.get_or_create(
                plate_number=vehicle_data['plate_number'],
                defaults={**vehicle_data, 'customer': customers[i]}
            )
            if created:
                print(f"✓ Created vehicle: {vehicle.plate_number} for {vehicle.customer.full_name}")

    # Create sample orders
    order_types = ['service', 'sales', 'consultation']
    statuses = ['created', 'assigned', 'in_progress', 'completed', 'cancelled']
    priorities = ['low', 'medium', 'high', 'urgent']

    for i in range(10):
        if customers:
            customer = random.choice(customers)
            vehicle = customer.vehicles.first()
            
            order_data = {
                'customer': customer,
                'vehicle': vehicle,
                'type': random.choice(order_types),
                'status': random.choice(statuses),
                'priority': random.choice(priorities),
                'description': f'Sample order {i+1} description',
                'estimated_duration': random.randint(30, 180),
                'created_at': timezone.now() - timedelta(days=random.randint(0, 30))
            }

            order, created = Order.objects.get_or_create(
                order_number=f'ORD{str(i+1).zfill(3)}',
                defaults=order_data
            )
            if created:
                print(f"✓ Created order: {order.order_number} for {order.customer.full_name}")

    # Create sample inventory items
    inventory_items = [
        {'name': 'All-Season Tire', 'brand': 'Michelin', 'quantity': 20, 'price': 150.00},
        {'name': 'Engine Oil', 'brand': 'Castrol', 'quantity': 50, 'price': 25.00},
        {'name': 'Brake Pads', 'brand': 'Bosch', 'quantity': 15, 'price': 75.00},
        {'name': 'Air Filter', 'brand': 'Mann', 'quantity': 30, 'price': 15.00},
        {'name': 'Spark Plugs', 'brand': 'NGK', 'quantity': 40, 'price': 8.00},
    ]

    for item_data in inventory_items:
        item, created = InventoryItem.objects.get_or_create(
            name=item_data['name'],
            brand=item_data['brand'],
            defaults=item_data
        )
        if created:
            print(f"✓ Created inventory item: {item.name} - {item.brand}")

if __name__ == '__main__':
    print("Initializing data...")
    create_admin_user()
    create_sample_data()
    print("\n🎉 Initialization complete!")
    print("You can now login with:")
    print("Username: admin")
    print("Password: admin123")
