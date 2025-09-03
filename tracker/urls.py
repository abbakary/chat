from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("customers/", views.customers_list, name="customers_list"),
    path("customers/search/", views.customers_search, name="customers_search"),
    path("customers/quick-create/", views.customers_quick_create, name="customers_quick_create"),
    path("customers/register/", views.customer_register, name="customer_register"),
    path("customers/export/", views.customers_export, name="customers_export"),
    path("customers/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("customers/<int:pk>/edit/", views.customer_edit, name="customer_edit"),
    path("customers/<int:pk>/order/new/", views.create_order_for_customer, name="create_order_for_customer"),

    path("orders/", views.orders_list, name="orders_list"),
    path("orders/export/", views.orders_export, name="orders_export"),
    path("orders/new/", views.order_start, name="order_start"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", views.update_order_status, name="update_order_status"),

    path("analytics/", views.analytics, name="analytics"),
    path("reports/", views.reports, name="reports"),
    path("reports/advanced/", views.reports_advanced, name="reports_advanced"),
    path("reports/export/", views.reports_export, name="reports_export"),

    # Inquiry management
    path("inquiries/", views.inquiries, name="inquiries"),
    path("inquiries/<int:pk>/", views.inquiry_detail, name="inquiry_detail"),
    path("inquiries/<int:pk>/respond/", views.inquiry_respond, name="inquiry_respond"),
    path("inquiries/<int:pk>/status/", views.update_inquiry_status, name="update_inquiry_status"),

    # Inventory (manager/admin)
    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/new/", views.inventory_create, name="inventory_create"),
    path("inventory/<int:pk>/edit/", views.inventory_edit, name="inventory_edit"),
    path("inventory/<int:pk>/delete/", views.inventory_delete, name="inventory_delete"),

    # Admin-only Organization Management
    path("organization/", views.organization_management, name="organization"),

    # User management (admin)
    path("users/", views.users_list, name="users_list"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),

    # Admin: system settings and tools
    path("admin/settings/", views.system_settings, name="system_settings"),
    path("admin/audit-logs/", views.audit_logs, name="audit_logs"),
    path("admin/backup/", views.backup_restore, name="backup_restore"),

    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("api/orders/recent/", views.api_recent_orders, name="api_recent_orders"),
    path("api/inventory/items/", views.api_inventory_items, name="api_inventory_items"),
    path("api/inventory/brands/", views.api_inventory_brands, name="api_inventory_brands"),
    path("api/inventory/stock/", views.api_inventory_stock, name="api_inventory_stock"),
]
