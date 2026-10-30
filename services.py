"""Serializers and business rules shared by the public and admin endpoints.

Every serializer returns snake_case keys that map one-to-one onto the
frontend types in `types/shoe.ts` (e.g. `original_price` -> `originalPrice`).
"""
import json
import random
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import bindparam, text

from extensions import db
from utils import execute, iso, money, num, query_all, query_one, query_scalar

# ============================================================
# Order lifecycle (mirrors lib/orderStatus.ts in the frontend)
# ============================================================

ORDER_STAGES = ['Placed', 'Confirmed', 'Packed', 'Shipped', 'Out for Delivery', 'Delivered']
ORDER_STATUSES = ORDER_STAGES + ['Cancelled']
PAYMENT_STATUSES = ['Paid', 'Pending', 'Refunded']
# Customers can cancel until the parcel leaves the workshop
CUSTOMER_CANCELLABLE = ['Placed', 'Confirmed', 'Packed']

STAGE_DEFAULTS = {
    'Placed': ('Harrison Bull Workshop', 'Your order has been placed and the workshop has been notified.'),
    'Confirmed': ('Harrison Bull Workshop', 'The workshop will review and accept your order.'),
    'Packed': ('Harrison Bull Workshop', 'Your shoes are being prepared, polished and packed.'),
    'Shipped': ('Dispatch Centre', 'Your parcel will be handed over to the courier.'),
    'Out for Delivery': ('Local Delivery Hub', 'Your parcel is with the delivery partner.'),
    'Delivered': (None, 'Delivered to your address.'),
}

STATUS_LABEL = {
    'Placed': 'Order Placed',
    'Confirmed': 'Order Accepted',
    'Packed': 'Preparing Order',
    'Shipped': 'Shipped',
    'Out for Delivery': 'Out for Delivery',
    'Delivered': 'Delivered',
    'Cancelled': 'Cancelled',
}

CUSTOMER_STATUS_MESSAGE = {
    'Placed': 'Your order {n} has been placed.',
    'Confirmed': 'Good news! Your order {n} has been accepted by the workshop.',
    'Packed': 'Your order {n} is being prepared.',
    'Shipped': 'Your order {n} has been shipped.',
    'Out for Delivery': 'Your order {n} is out for delivery today.',
    'Delivered': 'Your order {n} has been delivered. Enjoy your new shoes!',
    'Cancelled': 'Your order {n} has been cancelled.',
}

# Free shipping above this subtotal, flat fee otherwise (same rule as the cart)
FREE_SHIPPING_THRESHOLD = Decimal('300')
SHIPPING_FEE = Decimal('25')


def _in_query(sql, ids):
    stmt = text(sql).bindparams(bindparam('ids', expanding=True))
    return db.session.execute(stmt, {'ids': list(ids)}).mappings().all()


def _size_sort_key(size):
    match = re.search(r'\d+(\.\d+)?', size)
    return (float(match.group()) if match else 0, size)


# ============================================================
# Products
# ============================================================

PRODUCT_SELECT = '''
    SELECT p.*, c.name AS category_name, c.slug AS category_slug,
           ps.welt_type, ps.leather_type, ps.sole_type, ps.last_name,
           ps.lining_material, ps.crafting_time_hours, ps.crafting_operations,
           ps.is_resolable, ps.origin_location
    FROM products p
    JOIN categories c ON c.id = p.category_id
    LEFT JOIN product_specifications ps ON ps.product_id = p.id
'''


def serialize_products(rows):
    """Serialize product rows (from PRODUCT_SELECT) with images and sizes."""
    rows = list(rows)
    if not rows:
        return []
    ids = [r['id'] for r in rows]

    images = {}
    for img in _in_query(
        '''SELECT product_id, image_url FROM product_images
           WHERE product_id IN :ids ORDER BY is_primary DESC, display_order, created_at''', ids
    ):
        images.setdefault(img['product_id'], []).append(img['image_url'])

    sizes = {}
    for s in _in_query('SELECT product_id, size, stock_quantity FROM product_sizes WHERE product_id IN :ids', ids):
        sizes.setdefault(s['product_id'], {})[s['size']] = s['stock_quantity']

    result = []
    for r in rows:
        product_sizes = sizes.get(r['id'], {})
        hours = r['crafting_time_hours']
        result.append({
            'id': str(r['id']),
            'title': r['title'],
            'slug': r['slug'],
            'sku': r['sku'],
            'category_id': str(r['category_id']),
            'category': r['category_name'],
            'category_slug': r['category_slug'],
            'price': num(r['price']),
            'original_price': num(r['original_price']),
            'discount_percent': num(r['discount_percent']),
            'short_description': r['short_description'],
            'description': r['description'],
            'color': r['color'],
            'color_hex': r['color_hex'],
            'rating': num(r['rating']) or 0,
            'reviews_count': r['reviews_count'] or 0,
            'is_best_seller': bool(r['is_best_seller']),
            'is_featured': bool(r['is_featured']),
            'is_new': bool(r['is_new']),
            'in_stock': bool(r['in_stock']),
            'is_active': bool(r['is_active']),
            'images': images.get(r['id'], []),
            'sizes': dict(sorted(product_sizes.items(), key=lambda kv: _size_sort_key(kv[0]))),
            'specifications': {
                'welt_type': r['welt_type'],
                'leather_type': r['leather_type'],
                'sole_type': r['sole_type'],
                'last': r['last_name'],
                'lining': r['lining_material'],
                'crafting_time': f'{hours} Hours' if hours else None,
                'crafting_time_hours': hours,
                'crafting_operations': r['crafting_operations'],
                'resolable': bool(r['is_resolable']) if r['is_resolable'] is not None else None,
                'origin': r['origin_location'],
            },
            'created_at': iso(r['created_at']),
        })
    return result


def get_product_rows(where, **params):
    return query_all(f'{PRODUCT_SELECT} WHERE {where}', **params)


# ============================================================
# Coupons
# ============================================================

def serialize_coupon(c):
    is_percent = c['discount_type'] == 'percentage'
    value = num(c['discount_value'])
    expires_at = c['expires_at']
    return {
        'id': str(c['id']),
        'code': c['code'],
        'description': c['description'],
        'discount_type': c['discount_type'],
        'discount_value': value,
        'discount_percent': value if is_percent else None,
        'discount_amount': None if is_percent else value,
        'min_spend': num(c['min_order_amount']) or 0,
        'max_discount_amount': num(c['max_discount_amount']),
        'max_uses': c['max_uses'],
        'used_count': c['used_count'] or 0,
        'expires_at': iso(expires_at),
        'active': bool(c['is_active']),
        'is_expired': bool(expires_at and expires_at < datetime.utcnow()),
        'created_at': iso(c['created_at']),
    }


def round_half_up(value):
    return value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def evaluate_coupon(code, subtotal):
    """Check a coupon against a subtotal.

    Returns (coupon_row, discount_amount, error_message). The discount uses the
    same whole-unit rounding as the cart in the frontend so totals agree.
    """
    code = (code or '').strip().upper()
    if not code:
        return None, Decimal('0'), 'Coupon code required'

    coupon = query_one('SELECT * FROM coupons WHERE UPPER(code) = :code AND is_active = true', code=code)
    if not coupon:
        return None, Decimal('0'), 'Invalid or inactive promotional code.'
    if coupon['expires_at'] and coupon['expires_at'] < datetime.utcnow():
        return None, Decimal('0'), 'Coupon has expired'
    if coupon['max_uses'] is not None and (coupon['used_count'] or 0) >= coupon['max_uses']:
        return None, Decimal('0'), 'Coupon usage limit reached'

    subtotal = Decimal(str(subtotal))
    minimum = coupon['min_order_amount'] or Decimal('0')
    if subtotal < minimum:
        return None, Decimal('0'), f'Order subtotal must be at least ${minimum:g} to apply {coupon["code"]}.'

    value = coupon['discount_value']
    if coupon['discount_type'] == 'percentage':
        discount = round_half_up(subtotal * value / 100)
    else:
        discount = value
    if coupon['max_discount_amount'] is not None:
        discount = min(discount, coupon['max_discount_amount'])
    discount = min(discount, subtotal)
    return coupon, money(discount), None


# ============================================================
# Orders
# ============================================================

def generate_order_number():
    year = datetime.utcnow().year
    while True:
        number = f'HB-{year}-{random.randint(10000, 99999)}'
        if not query_scalar('SELECT 1 FROM orders WHERE order_number = :n', n=number):
            return number


def generate_tracking_number():
    return f'HB-EXP-{random.randint(1000000, 9999999)}'


def shipping_for(subtotal):
    return Decimal('0') if subtotal > FREE_SHIPPING_THRESHOLD or subtotal == 0 else SHIPPING_FEE


def init_tracking_logs(order_id, destination_city):
    for step, status in enumerate(ORDER_STAGES):
        location, description = STAGE_DEFAULTS[status]
        execute(
            '''INSERT INTO order_tracking_logs (order_id, step_order, status, location, description, completed, occurred_at)
               VALUES (:order_id, :step, :status, :location, :description, :completed, :occurred_at)''',
            order_id=order_id, step=step, status=status,
            location=location or destination_city or '',
            description=description,
            completed=(step == 0),
            occurred_at=datetime.utcnow() if step == 0 else None,
        )


def set_order_status(order_id, status, location=None, note=None):
    """Move an order to `status`, keeping the tracking timeline in step."""
    if status == 'Cancelled':
        execute(
            '''UPDATE orders SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP,
                      payment_status = CASE WHEN payment_status = 'Paid' THEN 'Refunded' ELSE payment_status END
               WHERE id = :id''', id=order_id)
        return

    target = ORDER_STAGES.index(status)
    for step, stage in enumerate(ORDER_STAGES):
        if step <= target:
            execute(
                '''UPDATE order_tracking_logs
                   SET completed = true,
                       occurred_at = COALESCE(occurred_at, CURRENT_TIMESTAMP)
                   WHERE order_id = :id AND status = :stage''', id=order_id, stage=stage)
        else:
            execute(
                '''UPDATE order_tracking_logs SET completed = false, occurred_at = NULL
                   WHERE order_id = :id AND status = :stage''', id=order_id, stage=stage)
    if location or note:
        execute(
            '''UPDATE order_tracking_logs
               SET location = COALESCE(:location, location), description = COALESCE(:note, description)
               WHERE order_id = :id AND status = :status''',
            id=order_id, status=status, location=location or None, note=note or None)
    execute('UPDATE orders SET status = :status, updated_at = CURRENT_TIMESTAMP WHERE id = :id',
            id=order_id, status=status)


def restock_order(order_id):
    """Return the reserved stock of a cancelled order to the shelves."""
    items = query_all('SELECT product_id, size, quantity FROM order_items WHERE order_id = :id', id=order_id)
    for item in items:
        execute(
            '''UPDATE product_sizes SET stock_quantity = stock_quantity + :qty, updated_at = CURRENT_TIMESTAMP
               WHERE product_id = :product_id AND size = :size''',
            qty=item['quantity'], product_id=item['product_id'], size=item['size'])
        refresh_product_stock(item['product_id'])
    execute('''UPDATE coupons SET used_count = GREATEST(used_count - 1, 0)
               WHERE id = (SELECT coupon_id FROM orders WHERE id = :id)''', id=order_id)


def refresh_product_stock(product_id):
    """Recompute total_stock_quantity / in_stock from the size rows."""
    total = query_scalar(
        'SELECT COALESCE(SUM(stock_quantity), 0) FROM product_sizes WHERE product_id = :id', id=product_id)
    execute(
        '''UPDATE products SET total_stock_quantity = :total, in_stock = :in_stock,
                  updated_at = CURRENT_TIMESTAMP WHERE id = :id''',
        total=total, in_stock=total > 0, id=product_id)


def add_notification(user_id, title, message, kind='order', order_id=None, product_id=None):
    if not user_id:
        return
    execute(
        '''INSERT INTO notifications (user_id, title, message, notification_type, related_order_id, related_product_id)
           VALUES (:user_id, :title, :message, :kind, :order_id, :product_id)''',
        user_id=user_id, title=title, message=message, kind=kind, order_id=order_id, product_id=product_id)


def notify_admins(title, message, order_id=None):
    execute(
        '''INSERT INTO notifications (user_id, title, message, notification_type, related_order_id)
           SELECT id, :title, :message, 'order', :order_id FROM users WHERE is_admin = true AND is_active = true''',
        title=title, message=message, order_id=order_id)


def notify_order_status(order, status):
    add_notification(
        order['user_id'],
        f'Order {STATUS_LABEL[status]}',
        CUSTOMER_STATUS_MESSAGE[status].format(n=order['order_number']),
        order_id=order['id'],
    )


ORDER_SELECT = '''
    SELECT o.*, u.id AS customer_id FROM orders o LEFT JOIN users u ON u.id = o.user_id
'''


def serialize_orders(rows, with_logs=True):
    rows = list(rows)
    if not rows:
        return []
    ids = [r['id'] for r in rows]

    items = {}
    for item in _in_query(
        '''SELECT oi.*, p.sku, p.color, c.name AS category,
                  (SELECT image_url FROM product_images WHERE product_id = oi.product_id
                   ORDER BY is_primary DESC, display_order LIMIT 1) AS image
           FROM order_items oi
           LEFT JOIN products p ON p.id = oi.product_id
           LEFT JOIN categories c ON c.id = p.category_id
           WHERE oi.order_id IN :ids ORDER BY oi.created_at''', ids
    ):
        items.setdefault(item['order_id'], []).append({
            'id': str(item['id']),
            'shoe_id': str(item['product_id']),
            'product_id': str(item['product_id']),
            'title': item['product_title'],
            'category': item['category'],
            'image': item['image'],
            'price': num(item['unit_price']),
            'size': item['size'],
            'color': item['color'],
            'quantity': item['quantity'],
            'sku': item['sku'],
            'subtotal': num(item['subtotal']),
        })

    logs = {}
    if with_logs:
        for log in _in_query(
            'SELECT * FROM order_tracking_logs WHERE order_id IN :ids ORDER BY step_order', ids
        ):
            logs.setdefault(log['order_id'], []).append({
                'status': log['status'],
                'timestamp': iso(log['occurred_at']),
                'location': log['location'],
                'description': log['description'],
                'completed': bool(log['completed']),
            })

    result = []
    for o in rows:
        data = {
            'id': str(o['id']),
            'order_number': o['order_number'],
            'customer_id': str(o['user_id']) if o['user_id'] else 'guest',
            'customer_name': o['customer_name'],
            'customer_email': o['customer_email'],
            'customer_phone': o['customer_phone'],
            'items': items.get(o['id'], []),
            'shipping_address': o['shipping_address'],
            'delivery_method': o['delivery_method'],
            'payment_method': o['payment_method'],
            'payment_status': o['payment_status'],
            'subtotal': num(o['subtotal']),
            'tax': num(o['tax']),
            'discount': num(o['discount_amount']),
            'coupon_code': o['coupon_code'],
            'shipping_fee': num(o['shipping_cost']),
            'total': num(o['total']),
            'status': o['status'],
            'created_at': iso(o['created_at']),
            'updated_at': iso(o['updated_at']),
            'estimated_delivery_date': o['estimated_delivery_date'],
            'tracking_number': o['tracking_number'],
            'courier': o['courier'],
            'special_instructions': o['notes'],
        }
        if with_logs:
            data['tracking_logs'] = logs.get(o['id'], [])
        result.append(data)
    return result


# ============================================================
# Users / addresses
# ============================================================

def serialize_user(u, stats=None):
    first, last = u['first_name'], u['last_name']
    data = {
        'id': str(u['id']),
        'name': f'{first} {last}'.strip(),
        'first_name': first,
        'last_name': last,
        'email': u['email'],
        'phone': u['phone'],
        'avatar_url': u['avatar_url'],
        'role': 'admin' if u['is_admin'] else 'customer',
        'is_admin': bool(u['is_admin']),
        'status': 'active' if u['is_active'] else 'suspended',
        'preferred_shoe_size': u['preferred_shoe_size'],
        'preferred_width': u['preferred_width'],
        'newsletter_subscribed': bool(u['newsletter_subscribed']),
        'promotions_enabled': bool(u['promotions_enabled']),
        'created_at': iso(u['created_at']),
    }
    if stats is not None:
        data['orders_count'] = stats.get('orders_count', 0)
        data['total_spent'] = stats.get('total_spent', 0.0)
    return data


def user_stats(user_ids):
    user_ids = list(user_ids)
    if not user_ids:
        return {}
    rows = _in_query(
        '''SELECT user_id, COUNT(*) AS orders_count, COALESCE(SUM(total), 0) AS total_spent
           FROM orders WHERE user_id IN :ids AND status <> 'Cancelled' GROUP BY user_id''', user_ids)
    return {r['user_id']: {'orders_count': r['orders_count'], 'total_spent': float(r['total_spent'])} for r in rows}


def serialize_address(a):
    full_name = f'{a["first_name"]} {a["last_name"]}'.strip()
    return {
        'id': str(a['id']),
        'full_name': full_name,
        'first_name': a['first_name'],
        'last_name': a['last_name'],
        'phone': a['phone'],
        'street': a['street_address'],
        'street_address': a['street_address'],
        'apartment': a['apartment'],
        'company_name': a['company_name'],
        'city': a['city'],
        'state': a['state'],
        'postal_code': a['postal_code'],
        'country': a['country'],
        'is_default': bool(a['is_default']),
        'is_default_shipping': bool(a['is_default']),
        'is_default_billing': bool(a['is_default']),
        'address_type': a['address_type'],
    }


# ============================================================
# Content: reviews, blog, stores, banners
# ============================================================

def serialize_review(r):
    return {
        'id': str(r['id']),
        'shoe_id': str(r['product_id']),
        'product_id': str(r['product_id']),
        'shoe_title': r.get('product_title'),
        'user_id': str(r['user_id']) if r['user_id'] else None,
        'user_name': r['customer_name'] or 'Anonymous',
        'rating': r['rating'],
        'title': r['title'],
        'comment': r['comment'],
        'verified_purchase': bool(r['verified_purchase']),
        'helpful_count': r['helpful_count'] or 0,
        'fit_feedback': r['fit_feedback'],
        'status': r['status'],
        'date': iso(r['created_at']),
    }


def refresh_product_rating(product_id):
    """Only approved reviews count towards the public rating."""
    stats = query_one(
        '''SELECT COALESCE(AVG(rating), 0) AS avg, COUNT(*) AS count FROM product_reviews
           WHERE product_id = :id AND status = 'Approved' ''', id=product_id)
    execute('UPDATE products SET rating = :rating, reviews_count = :count WHERE id = :id',
            rating=round(float(stats['avg']), 2), count=stats['count'], id=product_id)


BLOG_SELECT = '''
    SELECT b.*, COALESCE(b.author_name, NULLIF(TRIM(u.first_name || ' ' || u.last_name), '')) AS author
    FROM blog_posts b LEFT JOIN users u ON u.id = b.author_id
'''


def serialize_blog_post(b, with_content=True):
    data = {
        'id': str(b['id']),
        'slug': b['slug'],
        'title': b['title'],
        'excerpt': b['excerpt'],
        'read_time': b['read_time'],
        'publish_date': iso(b['published_at'] or b['created_at']),
        'author': b['author'],
        'author_role': b['author_role'],
        'image': b['featured_image_url'],
        'category': b['category'],
        'is_published': bool(b['is_published']),
    }
    if with_content:
        data['content'] = b['content']
    return data


def serialize_store(s, hours=None):
    parts = [s['street_address'], s['city']]
    region = ' '.join(x for x in [s['state'], s['postal_code']] if x)
    if region:
        parts.append(region)
    parts.append(s['country'])
    return {
        'id': str(s['id']),
        'name': s['name'],
        'city': s['city'],
        'state': s['state'],
        'country': s['country'],
        'postal_code': s['postal_code'],
        'street': s['street_address'],
        'address': ', '.join(p for p in parts if p),
        'phone': s['phone'],
        'email': s['email'],
        'hours': s['hours_text'] or (hours_summary(hours) if hours else None),
        'hours_by_day': hours,
        'image': s['image_url'],
        'description': s['description'],
        'appointment_available': bool(s['appointment_available']),
        'services': s['services'] or [],
        'coordinates': {'lat': num(s['latitude']), 'lng': num(s['longitude'])}
        if s['latitude'] is not None and s['longitude'] is not None else None,
        'is_active': bool(s['is_active']),
    }


DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']


def store_hours_by_day(store_ids):
    store_ids = list(store_ids)
    if not store_ids:
        return {}
    result = {}
    for h in _in_query(
        'SELECT * FROM store_hours WHERE store_id IN :ids ORDER BY day_of_week', store_ids
    ):
        result.setdefault(h['store_id'], {})[DAY_NAMES[h['day_of_week']]] = {
            'opening_time': h['opening_time'].strftime('%H:%M') if h['opening_time'] else None,
            'closing_time': h['closing_time'].strftime('%H:%M') if h['closing_time'] else None,
            'is_closed': bool(h['is_closed']) or not h['opening_time'],
        }
    return result


def hours_summary(hours):
    lines = []
    for day in DAY_NAMES[1:] + DAY_NAMES[:1]:
        info = hours.get(day)
        if info and not info['is_closed']:
            lines.append(f'{day[:3]}: {info["opening_time"]} - {info["closing_time"]}')
    return ' • '.join(lines) or None


def serialize_banner(b):
    return {
        'id': str(b['id']),
        'title': b['title'],
        'subtitle': b['subtitle'] or b['description'],
        'badge': b['badge'],
        'button_text': b['button_text'],
        'link': b['link_url'],
        'image_url': b['image_url'],
        'active': bool(b['is_active']),
        'background_color': b['background_color'],
        'display_order': b['display_order'],
        'start_date': iso(b['start_date']),
        'end_date': iso(b['end_date']),
    }


def to_json(value):
    return json.dumps(value) if value is not None else None
