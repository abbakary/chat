from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0002_alter_customer_customer_type'),
    ]

    operations = [
        # Customer indexes
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['full_name'], name='idx_cust_name'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['phone'], name='idx_cust_phone'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['email'], name='idx_cust_email'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['registration_date'], name='idx_cust_reg'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['last_visit'], name='idx_cust_lastvisit'),
        ),
        migrations.AddIndex(
            model_name='customer',
            index=models.Index(fields=['customer_type'], name='idx_cust_type'),
        ),

        # Vehicle indexes
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['customer'], name='idx_vehicle_customer'),
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['plate_number'], name='idx_vehicle_plate'),
        ),

        # Order indexes
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status'], name='idx_order_status'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['type'], name='idx_order_type'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['priority'], name='idx_order_priority'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['created_at'], name='idx_order_created'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['completed_at'], name='idx_order_completed'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['customer', 'created_at'], name='idx_order_cust_created'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['type', 'status'], name='idx_order_type_status'),
        ),

        # InventoryItem indexes
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['name'], name='idx_item_name'),
        ),
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['brand'], name='idx_item_brand'),
        ),
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['name', 'brand'], name='idx_item_name_brand'),
        ),
        migrations.AddIndex(
            model_name='inventoryitem',
            index=models.Index(fields=['created_at'], name='idx_item_created'),
        ),
    ]
