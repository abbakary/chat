from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.contrib import messages
from django.db.models.functions import TruncDate
from django.core.cache import cache
import json
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from .models import Customer, Order, Vehicle, InventoryItem
from .forms import (
    CustomerStep1Form,
    CustomerStep2Form,
    CustomerStep3Form,
    CustomerStep4Form,
    VehicleForm,
    OrderForm,
    CustomerEditForm,
)


class CustomLoginView(LoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        remember = self.request.POST.get("remember")
        if not remember:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(60 * 60 * 24 * 14)
        return response

    def get_success_url(self):
        user = self.request.user
        # Admins land on dashboard
        if user.is_superuser:
            return reverse('tracker:dashboard')
        # Managers land on orders list (operational focus)
        if user.groups.filter(name='manager').exists():
            return reverse('tracker:orders_list')
        # Staff (non-admin) to users list, otherwise dashboard
        if user.is_staff:
            return reverse('tracker:users_list')
        return reverse('tracker:dashboard')


@login_required
def dashboard(request: HttpRequest):
    cache_key = "dashboard_metrics_v1"
    cached = cache.get(cache_key)
    if cached:
        (
            total_orders,
            total_customers,
            status_counts,
            type_counts,
            priority_counts,
            completed_today_count,
            trend_labels,
            trend_values,
            total_stock,
        ) = cached
    else:
        total_orders = Order.objects.count()
        total_customers = Customer.objects.count()
        status_counts_qs = Order.objects.values("status").annotate(c=Count("id"))
        type_counts_qs = Order.objects.values("type").annotate(c=Count("id"))
        priority_counts_qs = Order.objects.values("priority").annotate(c=Count("id"))
        status_counts = {x["status"]: x["c"] for x in status_counts_qs}
        type_counts = {x["type"]: x["c"] for x in type_counts_qs}
        priority_counts = {x["priority"]: x["c"] for x in priority_counts_qs}
        today = timezone.localdate()
        completed_today_count = Order.objects.filter(status="completed", completed_at__date=today).count()
        dates = [today - timezone.timedelta(days=i) for i in range(13, -1, -1)]
        trend_qs = (
            Order.objects.annotate(day=TruncDate("created_at")).values("day").annotate(c=Count("id"))
        )
        trend_map = {row["day"]: row["c"] for row in trend_qs}
        trend_labels = [d.strftime("%Y-%m-%d") for d in dates]
        trend_values = [trend_map.get(d, 0) for d in dates]
        total_stock = InventoryItem.objects.aggregate(total=Sum('quantity'))['total'] or 0
        cache.set(cache_key, (
            total_orders,
            total_customers,
            status_counts,
            type_counts,
            priority_counts,
            completed_today_count,
            trend_labels,
            trend_values,
            total_stock,
        ), 60)

    today = timezone.localdate()
    pending_count = status_counts.get("created", 0)
    in_progress_count = status_counts.get("in_progress", 0)
    active_count = status_counts.get("created", 0) + status_counts.get("assigned", 0) + status_counts.get("in_progress", 0)
    recent_orders = (
        Order.objects.select_related("customer", "vehicle")
        .exclude(status="completed")
        .order_by("-created_at")[:10]
    )
    inventory_preview = InventoryItem.objects.order_by("-created_at")[:10]
    can_manage_inventory = (request.user.is_superuser or request.user.groups.filter(name='manager').exists())
    completed = status_counts.get("completed", 0)
    completed_percent = int((completed * 100) / total_orders) if total_orders else 0
    charts = {
        "status": {
            "labels": ["Created", "Assigned", "In Progress", "Completed", "Cancelled"],
            "values": [
                status_counts.get("created", 0),
                status_counts.get("assigned", 0),
                status_counts.get("in_progress", 0),
                status_counts.get("completed", 0),
                status_counts.get("cancelled", 0),
            ],
        },
        "type": {
            "labels": ["Service", "Sales", "Consultation"],
            "values": [
                type_counts.get("service", 0),
                type_counts.get("sales", 0),
                type_counts.get("consultation", 0),
            ],
        },
        "priority": {
            "labels": ["Low", "Medium", "High", "Urgent"],
            "values": [
                priority_counts.get("low", 0),
                priority_counts.get("medium", 0),
                priority_counts.get("high", 0),
                priority_counts.get("urgent", 0),
            ],
        },
        "trend": {"labels": trend_labels, "values": trend_values},
    }

    return render(
        request,
        "tracker/dashboard.html",
        {
            "total_orders": total_orders,
            "total_customers": total_customers,
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
            "completed_today_count": completed_today_count,
            "active_count": active_count,
            "status_counts": status_counts,
            "type_counts": type_counts,
            "recent_orders": recent_orders,
            "completed_percent": completed_percent,
            "charts_json": json.dumps(charts),
            "inventory_preview": inventory_preview,
            "can_manage_inventory": can_manage_inventory,
            "total_stock": total_stock,
        },
    )


@login_required
@login_required
def customers_list(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = Customer.objects.all().order_by('-registration_date')
    if q:
        qs = qs.filter(full_name__icontains=q)
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    customers = paginator.get_page(page)
    return render(request, "tracker/customers_list.html", {"customers": customers, "q": q})


@login_required
def customers_search(request: HttpRequest):
    q = request.GET.get("q", "").strip()
    customer_id = request.GET.get("id")
    recent = request.GET.get("recent")
    details = request.GET.get("details")

    results = []

    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id)
            results = [customer]
        except Customer.DoesNotExist:
            pass
    elif recent:
        results = Customer.objects.all().order_by('-last_visit', '-registration_date')[:10]
    elif q:
        results = Customer.objects.filter(
            Q(full_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q) |
            Q(code__icontains=q)
        ).order_by('-last_visit', '-registration_date')[:20]

    data = []
    for c in results:
        item = {
            "id": c.id,
            "code": c.code,
            "name": c.full_name,
            "phone": c.phone,
            "email": c.email or '',
            "type": c.customer_type or 'personal',
            "last_visit": c.last_visit.isoformat() if c.last_visit else None,
            "total_visits": c.total_visits,
            "address": c.address or '',
        }
        if details and customer_id:
            item.update({
                "organization_name": c.organization_name or '',
                "tax_number": c.tax_number or '',
                "personal_subtype": c.personal_subtype or '',
                "current_status": c.current_status or '',
                "registration_date": c.registration_date.isoformat() if c.registration_date else None,
                "vehicles": [
                    {"id": v.id, "plate_number": v.plate_number, "make": v.make or '', "model": v.model or ''}
                    for v in c.vehicles.all()
                ],
                "orders": [
                    {"id": o.id, "order_number": o.order_number, "type": o.type, "status": o.status, "created_at": o.created_at.isoformat()}
                    for o in c.orders.order_by('-created_at')[:5]
                ],
            })
        data.append(item)
    return JsonResponse({"results": data})


@login_required
def customer_detail(request: HttpRequest, pk: int):
    c = get_object_or_404(Customer, pk=pk)
    vehicles = c.vehicles.all()
    orders = c.orders.order_by("-created_at")[:20]
    return render(request, "tracker/customer_detail.html", {"customer": c, "vehicles": vehicles, "orders": orders})


@login_required
def customer_register(request: HttpRequest):
    step = int(request.POST.get("step", request.GET.get("step", 1)))
    if request.method == "POST":
        if step == 1:
            form = CustomerStep1Form(request.POST)
            action = request.POST.get("action")
            if form.is_valid():
                if action == "save_customer":
                    data = form.cleaned_data
                    c = Customer.objects.create(
                        full_name=data.get("full_name"),
                        phone=data.get("phone"),
                        email=data.get("email"),
                        address=data.get("address"),
                        notes=data.get("notes"),
                    )
                    messages.success(request, "Customer saved successfully")
                    return redirect("tracker:customer_detail", pk=c.id)
                # Continue to next step
                request.session["reg_step1"] = form.cleaned_data
                return redirect(f"{reverse('tracker:customer_register')}?step=2")
        elif step == 2:
            form = CustomerStep2Form(request.POST)
            if form.is_valid():
                request.session["reg_step2"] = form.cleaned_data
                intent = form.cleaned_data.get("intent")
                next_step = 4 if intent == "inquiry" else 3
                return redirect(f"{reverse('tracker:customer_register')}?step={next_step}")
        elif step == 3:
            form = CustomerStep3Form(request.POST)
            if form.is_valid():
                request.session["reg_step3"] = form.cleaned_data
                return redirect(f"{reverse('tracker:customer_register')}?step=4")
        elif step == 4:
            form = CustomerStep4Form(request.POST)
            vehicle_form = VehicleForm(request.POST)
            order_form = OrderForm(request.POST)
            if form.is_valid() and order_form.is_valid():
                inv_check_ok = True
                if order_form.cleaned_data.get('type') == 'sales':
                    name = order_form.cleaned_data.get('item_name')
                    brand = order_form.cleaned_data.get('brand')
                    qty = order_form.cleaned_data.get('quantity') or 0
                    item = InventoryItem.objects.filter(name=name, brand=brand).first()
                    if not item:
                        messages.error(request, 'Item not found in inventory')
                        inv_check_ok = False
                    elif item.quantity < qty:
                        messages.error(request, f'Only {item.quantity} in stock for {name} ({brand})')
                        inv_check_ok = False
                if not inv_check_ok:
                    context = {"step": 4, "form": form, "vehicle_form": vehicle_form, "order_form": order_form}
                    return render(request, "tracker/customer_register.html", context)
                data = {**request.session.get("reg_step1", {}), **form.cleaned_data}
                c = Customer.objects.create(
                    full_name=data.get("full_name"),
                    phone=data.get("phone"),
                    email=data.get("email"),
                    address=data.get("address"),
                    notes=data.get("notes"),
                    customer_type=data.get("customer_type"),
                    organization_name=data.get("organization_name"),
                    tax_number=data.get("tax_number"),
                    personal_subtype=data.get("personal_subtype"),
                )
                v = None
                if vehicle_form.is_valid() and any(vehicle_form.cleaned_data.values()):
                    v = vehicle_form.save(commit=False)
                    v.customer = c
                    v.save()
                o = order_form.save(commit=False)
                o.customer = c
                o.vehicle = v
                o.status = "created"
                if o.type == "service":
                    pass
                o.save()
                if o.type == 'sales':
                    from .utils import adjust_inventory
                    adjust_inventory(o.item_name, o.brand, -(o.quantity or 0))
                for key in ["reg_step1", "reg_step2", "reg_step3"]:
                    request.session.pop(key, None)
                messages.success(request, "Customer registered and order created successfully")
                return redirect("tracker:customer_detail", pk=c.id)
            else:
                messages.error(request, "Please correct the highlighted errors and try again")
    # GET or invalid POST
    context = {"step": step}
    # Read previously selected intent for conditional rendering
    session_step2 = request.session.get("reg_step2", {}) or {}
    intent = session_step2.get("intent")
    context["intent"] = intent
    if step == 1:
        context["form"] = CustomerStep1Form(initial=request.session.get("reg_step1"))
    elif step == 2:
        context["form"] = CustomerStep2Form(initial=session_step2)
    elif step == 3:
        context["form"] = CustomerStep3Form(initial=request.session.get("reg_step3"))
    else:
        context["form"] = CustomerStep4Form()
        context["vehicle_form"] = VehicleForm()
        # Include previous steps for summary
        context["step1"] = request.session.get("reg_step1", {})
        context["step2"] = session_step2
        context["step3"] = request.session.get("reg_step3", {})
        # Prefill order type based on intent and selected services
        type_map = {"service": "service", "sales": "sales", "inquiry": "consultation"}
        order_initial = {"type": type_map.get(intent)} if intent in type_map else {}
        sel_services = context["step3"].get("service_type") or []
        if sel_services:
            order_initial["service_selection"] = sel_services
        context["order_form"] = OrderForm(initial=order_initial)
    return render(request, "tracker/customer_register.html", context)


@login_required
def create_order_for_customer(request: HttpRequest, pk: int):
    from .utils import adjust_inventory
    c = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        form = OrderForm(request.POST)
        # Ensure vehicle belongs to this customer
        form.fields["vehicle"].queryset = c.vehicles.all()
        if form.is_valid():
            o = form.save(commit=False)
            o.customer = c
            o.status = "created"
            # Inventory check for sales
            if o.type == 'sales':
                name = (o.item_name or '').strip()
                brand = (o.brand or '').strip()
                qty = int(o.quantity or 0)
                from django.db.models import Sum, Q
                if (brand or '').lower() == 'unbranded':
                    available = InventoryItem.objects.filter(name=name).filter(Q(brand__isnull=True) | Q(brand="")).aggregate(total=Sum('quantity')).get('total') or 0
                else:
                    available = InventoryItem.objects.filter(name=name, brand=brand).aggregate(total=Sum('quantity')).get('total') or 0
                if not name or not brand or qty <= 0:
                    messages.error(request, 'Item, brand and valid quantity are required')
                    return render(request, "tracker/order_create.html", {"customer": c, "form": form})
                if available < qty:
                    messages.error(request, f'Only {available} in stock for {name} ({brand})')
                    return render(request, "tracker/order_create.html", {"customer": c, "form": form})
            o.save()
            # Deduct inventory after save
            if o.type == 'sales':
                ok, _, remaining = adjust_inventory(o.item_name, o.brand, -(o.quantity or 0))
                if ok:
                    messages.success(request, f"Order created. Remaining stock for {o.item_name} ({o.brand}): {remaining}")
                else:
                    messages.warning(request, 'Order created, but inventory not adjusted')
            else:
                messages.success(request, "Order created successfully")
            return redirect("tracker:order_detail", pk=o.id)
        else:
            messages.error(request, "Please fix form errors and try again")
    else:
        form = OrderForm()
        form.fields["vehicle"].queryset = c.vehicles.all()
    return render(request, "tracker/order_create.html", {"customer": c, "form": form})


@login_required
def orders_list(request: HttpRequest):
    status = request.GET.get("status", "all")
    type_ = request.GET.get("type", "all")
    qs = Order.objects.select_related("customer", "vehicle").order_by("-created_at")
    if status != "all":
        qs = qs.filter(status=status)
    if type_ != "all":
        qs = qs.filter(type=type_)
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    return render(request, "tracker/orders_list.html", {"orders": orders, "status": status, "type": type_})


@login_required
def order_start(request: HttpRequest):
    # Support GET ?customer=<id> to go straight into order form for that customer
    if request.method == 'GET':
        cust_id = request.GET.get('customer')
        if cust_id:
            c = get_object_or_404(Customer, pk=cust_id)
            form = OrderForm()
            form.fields['vehicle'].queryset = c.vehicles.all()
            return render(request, "tracker/order_create.html", {"customer": c, "form": form})
        form = OrderForm()
        try:
            form.fields['vehicle'].queryset = Vehicle.objects.none()
        except Exception:
            pass
        return render(request, "tracker/order_create.html", {"form": form})

    # Handle POST (AJAX or standard form submit)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        customer_id = request.POST.get('customer_id')
        if not customer_id:
            return JsonResponse({'success': False, 'message': 'Customer ID is required'})
        customer = get_object_or_404(Customer, id=customer_id)
        order_data = {
            'customer': customer,
            'type': request.POST.get('type'),
            'priority': request.POST.get('priority', 'medium'),
            'status': 'created',
            'description': request.POST.get('description', ''),
            'estimated_duration': request.POST.get('estimated_duration') or None,
            'item_name': request.POST.get('item_name', ''),
            'brand': request.POST.get('brand', ''),
            'quantity': request.POST.get('quantity') or None,
            'inquiry_type': request.POST.get('inquiry_type', ''),
            'questions': request.POST.get('questions', ''),
            'contact_preference': request.POST.get('contact_preference', ''),
            'follow_up_date': request.POST.get('follow_up_date') or None,
        }
        vehicle_id = request.POST.get('vehicle')
        if vehicle_id:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id, customer=customer)
            order_data['vehicle'] = vehicle
        if order_data.get('type') == 'sales':
            name = (order_data.get('item_name') or '').strip()
            brand = (order_data.get('brand') or '').strip()
            try:
                qty = int(order_data.get('quantity') or 0)
            except (TypeError, ValueError):
                qty = 0
            if not name or not brand or qty <= 0:
                return JsonResponse({'success': False, 'message': 'Item, brand and valid quantity are required', 'code': 'invalid'})
            item = InventoryItem.objects.filter(name=name, brand=brand).first()
            if not item:
                return JsonResponse({'success': False, 'message': 'Item not found in inventory', 'code': 'not_found'})
            if item.quantity < qty:
                return JsonResponse({'success': False, 'message': f'Only {item.quantity} in stock for {name} ({brand})', 'code': 'insufficient_stock', 'available': item.quantity})
        order = Order.objects.create(**order_data)
        remaining = None
        if order.type == 'sales':
            from .utils import adjust_inventory
            ok, status, rem = adjust_inventory(order.item_name, order.brand, -(order.quantity or 0))
            remaining = rem if ok else None
        return JsonResponse({'success': True, 'message': 'Order created successfully', 'order_id': order.id, 'remaining': remaining})

    # Standard form submit (non-AJAX)
    customer_id = request.POST.get('customer_id') or request.GET.get('customer')
    if not customer_id:
        messages.error(request, 'Customer is required to create an order')
        return render(request, "tracker/order_create.html")
    c = get_object_or_404(Customer, pk=customer_id)
    form = OrderForm(request.POST)
    form.fields['vehicle'].queryset = c.vehicles.all()
    if form.is_valid():
        o = form.save(commit=False)
        o.customer = c
        o.status = 'created'
        # Sales inventory validation
        if o.type == 'sales':
            name = (o.item_name or '').strip()
            brand = (o.brand or '').strip()
            qty = int(o.quantity or 0)
            from django.db.models import Q, Sum
            if (brand or '').lower() == 'unbranded':
                available = InventoryItem.objects.filter(name=name).filter(Q(brand__isnull=True) | Q(brand="")).aggregate(total=Sum('quantity')).get('total') or 0
            else:
                available = InventoryItem.objects.filter(name=name, brand=brand).aggregate(total=Sum('quantity')).get('total') or 0
            if not name or not brand or qty <= 0:
                messages.error(request, 'Item, brand and valid quantity are required')
                return render(request, "tracker/order_create.html", {"customer": c, "form": form})
            if available < qty:
                messages.error(request, f'Only {available} in stock for {name} ({brand})')
                return render(request, "tracker/order_create.html", {"customer": c, "form": form})
        o.save()
        if o.type == 'sales':
            from .utils import adjust_inventory
            ok, status, remaining = adjust_inventory(o.item_name, o.brand, -(o.quantity or 0))
            if ok:
                messages.success(request, f"Order created. Remaining stock for {o.item_name} ({o.brand}): {remaining}")
            else:
                messages.warning(request, 'Order created, but inventory not adjusted')
        else:
            messages.success(request, 'Order created successfully')
        return redirect('tracker:order_detail', pk=o.id)
    messages.error(request, 'Please fix form errors and try again')
    return render(request, "tracker/order_create.html", {"customer": c, "form": form})


@login_required
def order_detail(request: HttpRequest, pk: int):
    o = get_object_or_404(Order, pk=pk)
    return render(request, "tracker/order_detail.html", {"order": o})


@login_required
def update_order_status(request: HttpRequest, pk: int):
    o = get_object_or_404(Order, pk=pk)
    status = request.POST.get("status")
    now = timezone.now()
    if status in dict(Order.STATUS_CHOICES):
        o.status = status
        if status == "assigned":
            o.assigned_at = now
        elif status == "in_progress":
            o.started_at = now
        elif status == "completed":
            o.completed_at = now
            if o.started_at:
                o.actual_duration = int((now - o.started_at).total_seconds() // 60)
            c = o.customer
            c.total_spent = c.total_spent + 0  # integrate billing later
            c.last_visit = now
            c.current_status = "completed"
            c.save()
        elif status == "cancelled":
            o.cancelled_at = now
            # Restock on cancellation for sales orders
            if o.type == 'sales' and (o.quantity or 0) > 0 and o.item_name and o.brand:
                from .utils import adjust_inventory
                adjust_inventory(o.item_name, o.brand, (o.quantity or 0))
        o.save()
        messages.success(request, f"Order status updated to {status.replace('_',' ').title()}")
    else:
        messages.error(request, "Invalid status")
    return redirect("tracker:order_detail", pk=o.id)


@login_required
def analytics(request: HttpRequest):
    from datetime import timedelta
    period = request.GET.get('period', 'monthly')

    today = timezone.localdate()
    if period == 'daily':
        start_date = today
        end_date = today
        labels = [f"{i:02d}:00" for i in range(24)]
    elif period == 'weekly':
        start_date = today - timedelta(days=6)
        end_date = today
        labels = [(start_date + timedelta(days=i)).strftime('%a') for i in range(7)]
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today
        labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    else:  # monthly
        start_date = today - timedelta(days=29)
        end_date = today
        labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]

    qs = Order.objects.filter(created_at__date__range=[start_date, end_date])
    status_counts = {row['status']: row['c'] for row in qs.values('status').annotate(c=Count('id'))}
    type_counts = {row['type']: row['c'] for row in qs.values('type').annotate(c=Count('id'))}
    priority_counts = {row['priority']: row['c'] for row in qs.values('priority').annotate(c=Count('id'))}

    # Trend by selected period
    if period == 'daily':
        from django.db.models.functions import ExtractHour
        trend_map = {int(row['h'] or 0): row['c'] for row in qs.annotate(h=ExtractHour('created_at')).values('h').annotate(c=Count('id'))}
        trend_values = [trend_map.get(h, 0) for h in range(24)]
        trend_labels = labels
    elif period == 'weekly':
        by_date = {row['day']: row['c'] for row in qs.annotate(day=TruncDate('created_at')).values('day').annotate(c=Count('id'))}
        trend_values = []
        for i in range(7):
            d = start_date + timezone.timedelta(days=i)
            trend_values.append(by_date.get(d, 0))
        trend_labels = labels
    elif period == 'yearly':
        from django.db.models.functions import ExtractMonth
        by_month = {int(row['m']): row['c'] for row in qs.annotate(m=ExtractMonth('created_at')).values('m').annotate(c=Count('id'))}
        trend_values = [by_month.get(i, 0) for i in range(1, 13)]
        trend_labels = labels
    else:  # monthly
        by_date = {row['day']: row['c'] for row in qs.annotate(day=TruncDate('created_at')).values('day').annotate(c=Count('id'))}
        trend_values = []
        for i in range(30):
            d = start_date + timezone.timedelta(days=i)
            trend_values.append(by_date.get(d, 0))
        trend_labels = labels

    charts = {
        'status': {
            'labels': ['Created','Assigned','In Progress','Completed','Cancelled'],
            'values': [
                status_counts.get('created',0),
                status_counts.get('assigned',0),
                status_counts.get('in_progress',0),
                status_counts.get('completed',0),
                status_counts.get('cancelled',0),
            ]
        },
        'type': {
            'labels': ['Service','Sales','Consultation'],
            'values': [
                type_counts.get('service',0),
                type_counts.get('sales',0),
                type_counts.get('consultation',0),
            ]
        },
        'priority': {
            'labels': ['Low','Medium','High','Urgent'],
            'values': [
                priority_counts.get('low',0),
                priority_counts.get('medium',0),
                priority_counts.get('high',0),
                priority_counts.get('urgent',0),
            ]
        },
        'trend': { 'labels': trend_labels, 'values': trend_values },
    }

    totals = {
        'total_orders': qs.count(),
        'completed': qs.filter(status='completed').count(),
        'in_progress': qs.filter(status__in=['created','assigned','in_progress']).count(),
        'customers': Customer.objects.filter(registration_date__date__range=[start_date, end_date]).count(),
    }

    return render(request, 'tracker/analytics.html', {
        'charts_json': json.dumps(charts),
        'totals': totals,
        'period': period,
        'export_from': start_date.isoformat(),
        'export_to': end_date.isoformat(),
    })


@login_required
def reports(request: HttpRequest):
    f_from = request.GET.get("from")
    f_to = request.GET.get("to")
    f_type = request.GET.get("type", "all")
    qs = Order.objects.select_related("customer").order_by("-created_at")
    if f_from:
        try:
            qs = qs.filter(created_at__date__gte=f_from)
        except Exception:
            pass
    if f_to:
        try:
            qs = qs.filter(created_at__date__lte=f_to)
        except Exception:
            pass
    if f_type and f_type != "all":
        qs = qs.filter(type=f_type)

    total = qs.count()
    by_status = dict(qs.values_list("status").annotate(c=Count("id")))
    stats = {
        "total": total,
        "completed": by_status.get("completed", 0),
        "in_progress": by_status.get("in_progress", 0),
        "cancelled": by_status.get("cancelled", 0),
    }
    orders = list(qs[:300])
    return render(
        request,
        "tracker/reports.html",
        {"orders": orders, "stats": stats, "filters": {"from": f_from, "to": f_to, "type": f_type}},
    )

@login_required
def reports_export(request: HttpRequest):
    # Same filters as reports
    f_from = request.GET.get("from")
    f_to = request.GET.get("to")
    f_type = request.GET.get("type", "all")
    qs = Order.objects.select_related("customer").order_by("-created_at")
    if f_from:
        try:
            qs = qs.filter(created_at__date__gte=f_from)
        except Exception:
            pass
    if f_to:
        try:
            qs = qs.filter(created_at__date__lte=f_to)
        except Exception:
            pass
    if f_type and f_type != "all":
        qs = qs.filter(type=f_type)

    # Build CSV
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order", "Customer", "Type", "Status", "Priority", "Created At"])
    for o in qs.iterator():
        writer.writerow([o.order_number, o.customer.full_name, o.type, o.status, o.priority, o.created_at.isoformat()])
    return response

@login_required
def customers_export(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = Customer.objects.all().order_by('-registration_date')
    if q:
        qs = qs.filter(full_name__icontains=q)
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Code','Name','Phone','Type','Visits','Last Visit'])
    for c in qs.iterator():
        writer.writerow([c.code, c.full_name, c.phone, c.customer_type, c.total_visits, c.last_visit.isoformat() if c.last_visit else '' ])
    return response

@login_required
def orders_export(request: HttpRequest):
    status = request.GET.get('status','all')
    type_ = request.GET.get('type','all')
    qs = Order.objects.select_related('customer').order_by('-created_at')
    if status != 'all':
        qs = qs.filter(status=status)
    if type_ != 'all':
        qs = qs.filter(type=type_)
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    writer = csv.writer(response)
    writer.writerow(["Order","Customer","Type","Status","Priority","Created At"])
    for o in qs.iterator():
        writer.writerow([o.order_number, o.customer.full_name, o.type, o.status, o.priority, o.created_at.isoformat()])
    return response

@login_required
def api_recent_orders(request: HttpRequest):
    recents = Order.objects.select_related("customer", "vehicle").exclude(status="completed").order_by("-created_at")[:10]
    data = [
        {
            "order_number": r.order_number,
            "status": r.status,
            "type": r.type,
            "priority": r.priority,
            "customer": r.customer.full_name,
            "vehicle": r.vehicle.plate_number if r.vehicle else None,
            "created_at": r.created_at.isoformat(),
        }
        for r in recents
    ]
    return JsonResponse({"orders": data})

@login_required
def api_inventory_items(request: HttpRequest):
    from django.db.models import Sum
    cache_key = "api_inv_items_v1"
    data = cache.get(cache_key)
    if not data:
        rows = (
            InventoryItem.objects.values("name")
            .annotate(total=Sum("quantity"))
            .order_by("name")
        )
        items = [{"name": r["name"], "total_quantity": r["total"] or 0} for r in rows]
        data = {"items": items}
        cache.set(cache_key, data, 120)
    return JsonResponse(data)

@login_required
def api_inventory_brands(request: HttpRequest):
    from django.db.models import Sum, Min
    name = request.GET.get("name", "").strip()
    if not name:
        return JsonResponse({"brands": []})
    cache_key = f"api_inv_brands_{name}"
    data = cache.get(cache_key)
    if not data:
        # Aggregate by brand for this item
        rows = (
            InventoryItem.objects.filter(name=name)
            .values("brand")
            .annotate(quantity=Sum("quantity"), min_price=Min("price"))
            .order_by("brand")
        )
        non_empty = []
        unbranded_qty = 0
        unbranded_price = None
        for r in rows:
            b = (r["brand"] or "").strip()
            q = r["quantity"] or 0
            p = r["min_price"]
            if b:
                non_empty.append({"brand": b, "quantity": q, "price": str(p) if p is not None else ""})
            else:
                unbranded_qty += q
                if p is not None:
                    unbranded_price = p if unbranded_price is None else min(unbranded_price, p)
        brands = non_empty
        # Always include an aggregated Unbranded option when quantity exists
        if unbranded_qty > 0:
            brands.append({
                "brand": "Unbranded",
                "quantity": unbranded_qty,
                "price": str(unbranded_price) if unbranded_price is not None else ""
            })
        data = {"brands": brands}
        cache.set(cache_key, data, 120)
    return JsonResponse(data)

@login_required
def api_inventory_stock(request: HttpRequest):
    from django.db.models import Sum, Q
    name = request.GET.get("name", "").strip()
    brand = request.GET.get("brand", "").strip()
    if not name:
        return JsonResponse({"available": 0})
    # Treat special alias 'Unbranded' as brand is empty or null
    effective_brand = None if brand.lower() == 'unbranded' else brand
    cache_key = f"api_inv_stock_{name}_{(effective_brand or 'any')}"
    data = cache.get(cache_key)
    if data is None:
        qs = InventoryItem.objects.filter(name=name)
        if effective_brand is not None and effective_brand != "":
            qs = qs.filter(brand=effective_brand)
        elif brand.lower() == 'unbranded':
            qs = qs.filter(Q(brand__isnull=True) | Q(brand=""))
        total = qs.aggregate(total=Sum("quantity")).get("total") or 0
        data = {"available": total}
        cache.set(cache_key, data, 60)
    return JsonResponse(data)

# Permissions
is_manager = user_passes_test(lambda u: u.is_authenticated and (u.is_superuser or u.groups.filter(name='manager').exists()))

@login_required
@is_manager
def inventory_list(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = InventoryItem.objects.all().order_by('-created_at')
    if q:
        qs = qs.filter(name__icontains=q)
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    items = paginator.get_page(page)
    return render(request, 'tracker/inventory_list.html', { 'items': items, 'q': q })

@login_required
@is_manager
def inventory_create(request: HttpRequest):
    from .forms import InventoryItemForm
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            from .utils import clear_inventory_cache
            clear_inventory_cache(item.name, item.brand)
            messages.success(request, 'Inventory item created')
            return redirect('tracker:inventory_list')
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = InventoryItemForm()
    return render(request, 'tracker/inventory_form.html', { 'form': form, 'mode': 'create' })

@login_required
@is_manager
def inventory_edit(request: HttpRequest, pk: int):
    from .forms import InventoryItemForm
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            from .utils import clear_inventory_cache
            clear_inventory_cache(item.name, item.brand)
            messages.success(request, 'Inventory item updated')
            return redirect('tracker:inventory_list')
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = InventoryItemForm(instance=item)
    return render(request, 'tracker/inventory_form.html', { 'form': form, 'mode': 'edit', 'item': item })

@login_required
@is_manager
def inventory_delete(request: HttpRequest, pk: int):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        from .utils import clear_inventory_cache
        name, brand = item.name, item.brand
        item.delete()
        clear_inventory_cache(name, brand)
        messages.success(request, 'Inventory item deleted')
        return redirect('tracker:inventory_list')
    return render(request, 'tracker/inventory_delete.html', { 'item': item })

# Admin-only: Organization Management
@login_required
@user_passes_test(lambda u: u.is_superuser)
def organization_management(request: HttpRequest):
    org_types = ['government', 'ngo', 'company']
    q = request.GET.get('q','').strip()
    qs = Customer.objects.filter(customer_type__in=org_types).order_by('-registration_date')
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q) | Q(organization_name__icontains=q) | Q(code__icontains=q))
    paginator = Paginator(qs, 20)
    page = request.GET.get('page')
    customers = paginator.get_page(page)
    type_counts = Customer.objects.filter(customer_type__in=org_types).values('customer_type').annotate(c=Count('id'))
    counts = {row['customer_type']: row['c'] for row in type_counts}
    total_org = sum(counts.values()) if counts else 0
    return render(request, 'tracker/organization.html', { 'customers': customers, 'q': q, 'counts': counts, 'total_org': total_org })

@login_required
@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def users_list(request: HttpRequest):
    q = request.GET.get('q','').strip()
    qs = User.objects.all().order_by('-date_joined')
    if q:
        qs = qs.filter(username__icontains=q)
    return render(request, 'tracker/users_list.html', { 'users': qs[:100], 'q': q })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_edit(request: HttpRequest, pk: int):
    from .forms import AdminUserForm
    u = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = AdminUserForm(request.POST, instance=u)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated')
            return redirect('tracker:users_list')
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = AdminUserForm(instance=u)
    return render(request, 'tracker/user_edit.html', { 'form': form, 'user_obj': u })


@login_required
def customer_edit(request: HttpRequest, pk: int):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        form = CustomerEditForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer updated successfully')
            return redirect('tracker:customer_detail', pk=customer.id)
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = CustomerEditForm(instance=customer)
    return render(request, 'tracker/customer_edit.html', { 'form': form, 'customer': customer })


@login_required
def customers_quick_create(request: HttpRequest):
    """Quick customer creation for order form"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            full_name = request.POST.get('full_name', '').strip()
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            customer_type = request.POST.get('customer_type', 'personal')

            if not full_name or not phone:
                return JsonResponse({'success': False, 'message': 'Name and phone are required'})

            # Check if customer with this phone already exists
            if Customer.objects.filter(phone=phone).exists():
                return JsonResponse({'success': False, 'message': 'Customer with this phone number already exists'})

            # Create customer
            customer = Customer.objects.create(
                full_name=full_name,
                phone=phone,
                email=email if email else None,
                customer_type=customer_type
            )

            return JsonResponse({
                'success': True,
                'message': 'Customer created successfully',
                'customer': {
                    'id': customer.id,
                    'name': customer.full_name,
                    'phone': customer.phone,
                    'email': customer.email or '',
                    'code': customer.code,
                    'type': customer.customer_type
                }
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error creating customer: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def inquiries(request: HttpRequest):
    """View and manage customer inquiries"""
    # Get filter parameters
    inquiry_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    follow_up = request.GET.get('follow_up', '')

    # Base queryset for consultation orders (inquiries)
    queryset = Order.objects.filter(type='consultation').select_related('customer').order_by('-created_at')

    # Apply filters
    if inquiry_type:
        queryset = queryset.filter(inquiry_type=inquiry_type)

    if status:
        queryset = queryset.filter(status=status)

    if follow_up == 'required':
        queryset = queryset.filter(follow_up_date__isnull=False)
    elif follow_up == 'overdue':
        today = timezone.localdate()
        queryset = queryset.filter(
            follow_up_date__lte=today,
            status__in=['created', 'in_progress']
        )

    # Pagination
    paginator = Paginator(queryset, 12)  # Show 12 inquiries per page
    page = request.GET.get('page')
    inquiries = paginator.get_page(page)

    # Statistics
    stats = {
        'new': Order.objects.filter(type='consultation', status='created').count(),
        'in_progress': Order.objects.filter(type='consultation', status='in_progress').count(),
        'resolved': Order.objects.filter(type='consultation', status='completed').count(),
    }

    context = {
        'inquiries': inquiries,
        'stats': stats,
        'today': timezone.localdate(),
    }

    return render(request, 'tracker/inquiries.html', context)


@login_required
def inquiry_detail(request: HttpRequest, pk: int):
    """Get inquiry details for modal view"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            inquiry = get_object_or_404(Order, pk=pk, type='consultation')

            data = {
                'id': inquiry.id,
                'customer': {
                    'name': inquiry.customer.full_name,
                    'phone': inquiry.customer.phone,
                    'email': inquiry.customer.email or '',
                },
                'inquiry_type': inquiry.inquiry_type or 'General',
                'contact_preference': inquiry.contact_preference or 'Phone',
                'questions': inquiry.questions or '',
                'status': inquiry.status,
                'status_display': inquiry.get_status_display(),
                'created_at': inquiry.created_at.isoformat(),
                'follow_up_date': inquiry.follow_up_date.isoformat() if inquiry.follow_up_date else None,
                'responses': [],  # In a real app, you'd have a related model for responses
            }

            return JsonResponse(data)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def inquiry_respond(request: HttpRequest, pk: int):
    """Respond to a customer inquiry"""
    from .utils import send_sms
    inquiry = get_object_or_404(Order, pk=pk, type='consultation')

    if request.method == 'POST':
        response_text = request.POST.get('response', '').strip()
        follow_up_required = request.POST.get('follow_up_required') == 'on'
        follow_up_date = request.POST.get('follow_up_date')

        if not response_text:
            messages.error(request, 'Response message is required')
            return redirect('tracker:inquiries')

        # Append response to inquiry notes
        stamp = timezone.now().strftime('%Y-%m-%d %H:%M')
        if inquiry.notes:
            inquiry.notes += f"\n\n[{stamp}] Response: {response_text}"
        else:
            inquiry.notes = f"[{stamp}] Response: {response_text}"

        # Update follow-up date if required
        if follow_up_required and follow_up_date:
            try:
                inquiry.follow_up_date = follow_up_date
            except ValueError:
                pass

        # Mark as in progress if not already completed
        if inquiry.status == 'created':
            inquiry.status = 'in_progress'

        inquiry.save()

        # Send SMS to the customer's phone
        phone = inquiry.customer.phone
        sms_message = f"Hello {inquiry.customer.full_name}, regarding your inquiry ({inquiry.inquiry_type or 'General'}): {response_text} — Superdoll Support"
        ok, info = send_sms(phone, sms_message)
        if ok:
            messages.success(request, 'Response sent via SMS')
        else:
            messages.warning(request, f'Response saved, but SMS not sent: {info}')
        return redirect('tracker:inquiries')

    return redirect('tracker:inquiries')


@login_required
def update_inquiry_status(request: HttpRequest, pk: int):
    """Update inquiry status"""
    inquiry = get_object_or_404(Order, pk=pk, type='consultation')

    if request.method == 'POST':
        new_status = request.POST.get('status')

        if new_status in ['created', 'in_progress', 'completed']:
            old_status = inquiry.status
            inquiry.status = new_status

            if new_status == 'completed':
                inquiry.completed_at = timezone.now()

            inquiry.save()

            status_display = {
                'created': 'New',
                'in_progress': 'In Progress',
                'completed': 'Resolved'
            }

            messages.success(request, f'Inquiry status updated to {status_display.get(new_status, new_status)}')
        else:
            messages.error(request, 'Invalid status')

    return redirect('tracker:inquiries')


@login_required
def reports_advanced(request: HttpRequest):
    """Advanced reports with period and type filters"""
    from datetime import timedelta

    period = request.GET.get('period', 'monthly')
    report_type = request.GET.get('type', 'overview')

    # Calculate date range based on period
    today = timezone.localdate()
    if period == 'daily':
        start_date = today
        end_date = today
        date_format = '%H:%M'
        labels = [f"{i:02d}:00" for i in range(24)]
    elif period == 'weekly':
        start_date = today - timedelta(days=6)
        end_date = today
        date_format = '%a'
        labels = [(start_date + timedelta(days=i)).strftime('%a') for i in range(7)]
    elif period == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today
        date_format = '%b'
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    else:  # monthly
        start_date = today - timedelta(days=29)
        end_date = today
        date_format = '%d'
        labels = [(start_date + timedelta(days=i)).strftime('%d') for i in range(30)]

    # Base statistics
    total_orders = Order.objects.filter(created_at__date__range=[start_date, end_date]).count()
    completed_orders = Order.objects.filter(
        created_at__date__range=[start_date, end_date],
        status='completed'
    ).count()
    pending_orders = Order.objects.filter(
        created_at__date__range=[start_date, end_date],
        status__in=['created', 'assigned', 'in_progress']
    ).count()
    total_customers = Customer.objects.filter(registration_date__date__range=[start_date, end_date]).count()

    completion_rate = int((completed_orders * 100) / total_orders) if total_orders > 0 else 0

    # Average duration
    avg_duration_qs = Order.objects.filter(
        created_at__date__range=[start_date, end_date],
        actual_duration__isnull=False
    ).aggregate(avg_duration=Avg('actual_duration'))
    avg_duration = int(avg_duration_qs['avg_duration'] or 0)

    stats = {
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders,
        'total_customers': total_customers,
        'completion_rate': completion_rate,
        'avg_duration': avg_duration,
        'new_customers': total_customers,
        'avg_service_time': avg_duration,
        # Order type breakdown
        'service_orders': Order.objects.filter(
            created_at__date__range=[start_date, end_date], type='service'
        ).count(),
        'sales_orders': Order.objects.filter(
            created_at__date__range=[start_date, end_date], type='sales'
        ).count(),
        'consultation_orders': Order.objects.filter(
            created_at__date__range=[start_date, end_date], type='consultation'
        ).count(),
    }

    # Calculate percentages
    if total_orders > 0:
        stats['service_percentage'] = int((stats['service_orders'] * 100) / total_orders)
        stats['sales_percentage'] = int((stats['sales_orders'] * 100) / total_orders)
        stats['consultation_percentage'] = int((stats['consultation_orders'] * 100) / total_orders)
    else:
        stats['service_percentage'] = stats['sales_percentage'] = stats['consultation_percentage'] = 0

    # Real trend data per selected period
    qs = Order.objects.filter(created_at__date__range=[start_date, end_date])
    if period == 'daily':
        from django.db.models.functions import ExtractHour
        trend_map = {int(r['h'] or 0): r['c'] for r in qs.annotate(h=ExtractHour('created_at')).values('h').annotate(c=Count('id'))}
        trend_values = [trend_map.get(h, 0) for h in range(24)]
    elif period == 'weekly':
        by_date = {r['day']: r['c'] for r in qs.annotate(day=TruncDate('created_at')).values('day').annotate(c=Count('id'))}
        trend_values = [(by_date.get(start_date + timedelta(days=i), 0)) for i in range(7)]
    elif period == 'yearly':
        from django.db.models.functions import ExtractMonth
        by_month = {int(r['m']): r['c'] for r in qs.annotate(m=ExtractMonth('created_at')).values('m').annotate(c=Count('id'))}
        trend_values = [by_month.get(i, 0) for i in range(1, 13)]
    else:  # monthly
        by_date = {r['day']: r['c'] for r in qs.annotate(day=TruncDate('created_at')).values('day').annotate(c=Count('id'))}
        trend_values = [(by_date.get(start_date + timedelta(days=i), 0)) for i in range(30)]

    chart_data = {
        'trend': { 'labels': labels, 'values': trend_values },
        'status': {
            'labels': ['Created', 'Assigned', 'In Progress', 'Completed', 'Cancelled'],
            'values': [
                qs.filter(status='created').count(),
                qs.filter(status='assigned').count(),
                qs.filter(status='in_progress').count(),
                qs.filter(status='completed').count(),
                qs.filter(status='cancelled').count(),
            ]
        },
        'orders': {
            'labels': ['Service', 'Sales', 'Consultation'],
            'values': [stats['service_orders'], stats['sales_orders'], stats['consultation_orders']]
        },
        'types': {
            'labels': ['Personal', 'Company', 'Government', 'NGO', 'Bodaboda'],
            'values': [
                Customer.objects.filter(registration_date__date__range=[start_date, end_date], customer_type='personal').count(),
                Customer.objects.filter(registration_date__date__range=[start_date, end_date], customer_type='company').count(),
                Customer.objects.filter(registration_date__date__range=[start_date, end_date], customer_type='government').count(),
                Customer.objects.filter(registration_date__date__range=[start_date, end_date], customer_type='ngo').count(),
                Customer.objects.filter(registration_date__date__range=[start_date, end_date], customer_type='bodaboda').count(),
            ]
        }
    }

    # Get data items based on report type
    if report_type == 'customers':
        data_items = Customer.objects.filter(
            registration_date__date__range=[start_date, end_date]
        ).order_by('-registration_date')[:20]
    elif report_type == 'inquiries':
        data_items = Order.objects.filter(
            created_at__date__range=[start_date, end_date],
            type='consultation'
        ).select_related('customer').order_by('-created_at')[:20]
    else:
        data_items = Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).select_related('customer').order_by('-created_at')[:20]

    context = {
        'period': period,
        'report_type': report_type,
        'stats': stats,
        'chart_data': json.dumps(chart_data),
        'data_items': data_items,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }

    return render(request, 'tracker/reports_advanced.html', context)

# ---------------------------
# System settings and admin
# ---------------------------
@login_required
@user_passes_test(lambda u: u.is_superuser)
def system_settings(request: HttpRequest):
    def defaults():
        return {
            'company_name': '',
            'default_priority': 'medium',
            'enable_unbranded_alias': True,
            'allow_order_without_vehicle': True,
            'sms_provider': 'none',
        }
    data = cache.get('system_settings', None) or defaults()
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST)
        if form.is_valid():
            data = {**defaults(), **form.cleaned_data}
            cache.set('system_settings', data, None)
            messages.success(request, 'Settings updated')
            return redirect('tracker:system_settings')
        else:
            messages.error(request, 'Please correct errors and try again')
    else:
        form = SystemSettingsForm(initial=data)
    return render(request, 'tracker/system_settings.html', {'form': form, 'settings': data})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def audit_logs(request: HttpRequest):
    logs = cache.get('audit_logs', [])
    return render(request, 'tracker/audit_logs.html', {'logs': logs})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def backup_restore(request: HttpRequest):
    if request.GET.get('download'):
        import json
        payload = {
            'system_settings': cache.get('system_settings', {}),
        }
        resp = HttpResponse(json.dumps(payload, indent=2), content_type='application/json')
        resp['Content-Disposition'] = 'attachment; filename="backup.json"'
        return resp
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'reset_settings':
            cache.delete('system_settings')
            messages.success(request, 'System settings have been reset to defaults')
            return redirect('tracker:backup_restore')
    return render(request, 'tracker/backup_restore.html')
