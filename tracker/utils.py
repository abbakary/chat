import os
import base64
import json
import os
from urllib import request, parse, error


def _post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[bool, str]:
    data = json.dumps(payload).encode('utf-8')
    req = request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            return 200 <= resp.status < 300, body
    except Exception as e:
        return False, str(e)


def send_sms(phone: str, message: str) -> tuple[bool, str]:
    """Send an SMS using either Zapier Catch Hook or Twilio REST API based on env configuration.
    Returns (success, info).
    Environment options:
      - ZAPIER_SMS_WEBHOOK_URL: If set, POSTs JSON {phone, message}
      - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM: If set, send via Twilio API
    """
    phone = (phone or '').strip()
    if not phone or not message:
        return False, "Missing phone or message"

    zapier_url = os.getenv('ZAPIER_SMS_WEBHOOK_URL')
    if zapier_url:
        ok, info = _post_json(zapier_url, {"phone": phone, "message": message})
        return ok, info

    # Twilio fallback via HTTP API
    sid = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    from_num = os.getenv('TWILIO_FROM')
    if sid and token and from_num:
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = parse.urlencode({
            'To': phone,
            'From': from_num,
            'Body': message,
        }).encode('utf-8')
        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        req = request.Request(twilio_url, data=data, headers={'Authorization': f'Basic {auth}'})
        try:
            with request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode('utf-8')
                return 200 <= resp.status < 300, body
        except Exception as e:
            return False, str(e)

    return False, "No SMS provider configured. Set ZAPIER_SMS_WEBHOOK_URL or Twilio env vars."


from django.core.cache import cache

def clear_inventory_cache(name: str | None = None, brand: str | None = None) -> None:
    try:
        cache.delete('api_inv_items_v1')
        cache.delete('dashboard_metrics_v1')
        if name:
            cache.delete(f'api_inv_brands_{name}')
            # Invalidate stock caches for specific brand, unbranded alias, and any-brand aggregate
            keys = {f"api_inv_stock_{name}_{brand or 'any'}", f"api_inv_stock_{name}_any"}
            if (brand or '').lower() == 'unbranded' or not (brand or '').strip():
                keys.add(f"api_inv_stock_{name}_any")
            for k in keys:
                cache.delete(k)
    except Exception:
        pass


def adjust_inventory(name: str, brand: str, qty_delta: int) -> tuple[bool, str, int | None]:
    """Adjust inventory by name+brand with qty_delta (negative to deduct, positive to restock).
    Returns (ok, status, remaining_qty). status in {ok, not_found, invalid}.
    """
    try:
        from .models import InventoryItem
        name = (name or '').strip()
        brand = (brand or '').strip()
        if not name:
            return False, 'invalid', None
        # Support alias 'Unbranded' which maps to empty/null brand rows
        if brand.lower() == 'unbranded':
            from django.db.models import Q
            item = InventoryItem.objects.filter(name=name).filter(Q(brand__isnull=True) | Q(brand="")).first()
        else:
            item = InventoryItem.objects.filter(name=name, brand=brand).first()
        if not item:
            return False, 'not_found', None
        new_qty = item.quantity + int(qty_delta)
        if new_qty < 0:
            new_qty = 0
        item.quantity = new_qty
        item.save()
        clear_inventory_cache(name, brand)
        return True, 'ok', new_qty
    except Exception as e:
        return False, str(e), None
