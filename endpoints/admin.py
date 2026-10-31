from datetime import datetime
import json
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import IntegrityError

from extensions import db
from services import (
    BLOG_SELECT, ORDER_SELECT, ORDER_STATUSES, PAYMENT_STATUSES, PRODUCT_SELECT, add_notification,
    get_product_rows, notify_order_status, refresh_product_rating, refresh_product_stock, restock_order,
    serialize_banner, serialize_blog_post, serialize_coupon, serialize_orders, serialize_products,
    serialize_review, serialize_store, serialize_user, set_order_status, store_hours_by_day, user_stats,
)
from utils import (
    admin_required, clean_str, error, execute, is_uuid, json_body, num, pagination, paging, query_all,
    query_one, query_scalar, slugify,
)

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

# Every admin route needs an authenticated admin.
@admin_bp.before_request
def check_admin():
    if request.method == 'OPTIONS':
        return None
    return admin_required(lambda: None)()


@admin_bp.errorhandler(IntegrityError)
def handle_integrity_error(exc):
    db.session.rollback()
    logger.warning(f'Integrity error: {exc.orig}')
    return error('A record with the same unique value (slug, SKU or code) already exists', 409)


# ------------------------------------------------------------
# Small SQL builders. Column names only ever come from the constants
# in this file, never from request keys, so they are safe to interpolate.
# ------------------------------------------------------------

JSONB_COLUMNS = {'services'}


def _placeholder(column):
    return f'CAST(:{column} AS jsonb)' if column in JSONB_COLUMNS else f':{column}'


def _prepare(values):
    return {k: (json.dumps(v) if k in JSONB_COLUMNS and v is not None else v) for k, v in values.items()}


def insert_row(table, values):
    columns = ', '.join(values)
    placeholders = ', '.join(_placeholder(c) for c in values)
    return query_one(f'INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING *', **_prepare(values))


def update_row(table, row_id, values):
    if not values:
        return query_one(f'SELECT * FROM {table} WHERE id = :id', id=row_id)
    assignments = ', '.join(f'{c} = {_placeholder(c)}' for c in values)
    return query_one(
        f'UPDATE {table} SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = :id RETURNING *',
        id=row_id, **_prepare(values))


def unique_slug(table, base, exclude_id=None):
    base = slugify(base) or 'item'
    slug, n = base, 1
    while query_scalar(f'SELECT 1 FROM {table} WHERE slug = :slug AND (CAST(:ex AS text) IS NULL OR id::text <> :ex)',
                       slug=slug, ex=exclude_id):
        n += 1
        slug = f'{base}-{n}'
    return slug


def pick(data, mapping):
    """Copy the keys in `mapping` ({column: (accepted request keys...)}) that are present in `data`."""
    values = {}
    for column, keys in mapping.items():
        for key in keys:
            if key in data:
                values[column] = data[key]
                break
    return values


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    except ValueError:
        raise ValueError(f'Invalid date: {value}')


def not_found(label):
    return error(f'{label} not found', 404)


# ============================================================
# Dashboard & analytics
# ============================================================

@admin_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Admin dashboard statistics"""
    try:
        by_status = {r['status']: r['count'] for r in query_all('SELECT status, COUNT(*) AS count FROM orders GROUP BY status')}
        recent = serialize_orders(
            query_all(f'{ORDER_SELECT} ORDER BY o.created_at DESC LIMIT 5'), with_logs=False)
        return jsonify({
            'total_users': query_scalar('SELECT COUNT(*) FROM users WHERE is_admin = false'),
            'total_orders': query_scalar('SELECT COUNT(*) FROM orders'),
            'total_products': query_scalar('SELECT COUNT(*) FROM products WHERE is_active = true'),
            'total_revenue': num(query_scalar("SELECT COALESCE(SUM(total), 0) FROM orders WHERE status <> 'Cancelled'")),
            'pending_orders': sum(by_status.get(s, 0) for s in ('Placed', 'Confirmed', 'Packed')),
            'low_stock_sizes': query_scalar('SELECT COUNT(*) FROM product_sizes WHERE stock_quantity <= 2'),
            'pending_reviews': query_scalar("SELECT COUNT(*) FROM product_reviews WHERE status = 'Pending'"),
            'unread_messages': query_scalar('SELECT COUNT(*) FROM contact_messages WHERE is_read = false'),
            'orders_by_status': by_status,
            'recent_orders': recent,
        }), 200

    except Exception as e:
        logger.error(f'Dashboard error: {str(e)}')
        return error('Failed to fetch dashboard', 500)


@admin_bp.route('/analytics/sales', methods=['GET'])
def get_sales_analytics():
    """Orders and revenue grouped by day, week or month (cancelled orders excluded)"""
    try:
        unit = {'daily': 'day', 'weekly': 'week', 'monthly': 'month'}.get(request.args.get('period', 'daily'), 'day')
        rows = query_all(
            f'''SELECT DATE_TRUNC('{unit}', created_at) AS date, COUNT(*) AS orders, COALESCE(SUM(total), 0) AS revenue
                FROM orders WHERE status <> 'Cancelled'
                GROUP BY 1 ORDER BY 1 DESC LIMIT 30''')
        return jsonify({'sales': [
            {'date': r['date'].isoformat(), 'orders': r['orders'], 'revenue': num(r['revenue'])} for r in rows
        ]}), 200

    except Exception as e:
        logger.error(f'Get sales analytics error: {str(e)}')
        return error('Failed to fetch analytics', 500)


# ============================================================
# Products
# ============================================================

PRODUCT_FIELDS = {
    'title': ('title',), 'slug': ('slug',), 'sku': ('sku',), 'price': ('price',),
    'original_price': ('original_price',), 'discount_percent': ('discount_percent',),
    'short_description': ('short_description',), 'description': ('description',),
    'color': ('color',), 'color_hex': ('color_hex',), 'is_best_seller': ('is_best_seller',),
    'is_featured': ('is_featured',), 'is_new': ('is_new',), 'is_active': ('is_active',),
}

SPEC_FIELDS = {
    'welt_type': ('welt_type',), 'leather_type': ('leather_type',), 'sole_type': ('sole_type',),
    'last_name': ('last', 'last_name'), 'lining_material': ('lining', 'lining_material'),
    'crafting_time_hours': ('crafting_time_hours',), 'crafting_operations': ('crafting_operations',),
    'is_resolable': ('resolable', 'is_resolable'), 'origin_location': ('origin', 'origin_location'),
}


def _resolve_category(data):
    if data.get('category_id'):
        return data['category_id'] if is_uuid(data['category_id']) else None
    name = clean_str(data.get('category'))
    if name:
        row = query_one('SELECT id FROM categories WHERE LOWER(name) = LOWER(:n) OR slug = LOWER(:n)', n=name)
        return row['id'] if row else None
    return False  # not supplied


def _save_product_children(product_id, data):
    """Replace images/sizes and upsert specifications when they are part of the request."""
    if isinstance(data.get('images'), list):
        execute('DELETE FROM product_images WHERE product_id = :id', id=product_id)
        for order, image in enumerate(u for u in data['images'] if isinstance(u, str) and u.strip()):
            execute(
                '''INSERT INTO product_images (product_id, image_url, alt_text, display_order, is_primary)
                   VALUES (:id, :url, :alt, :order, :primary)''',
                id=product_id, url=image.strip(), alt=clean_str(data.get('title')) or None,
                order=order, primary=(order == 0))

    if isinstance(data.get('sizes'), dict):
        sizes = {str(k).strip(): int(v) for k, v in data['sizes'].items() if str(k).strip()}
        if any(v < 0 for v in sizes.values()):
            raise ValueError('Stock quantities cannot be negative')
        for size, qty in sizes.items():
            execute(
                '''INSERT INTO product_sizes (product_id, size, stock_quantity) VALUES (:id, :size, :qty)
                   ON CONFLICT (product_id, size) DO UPDATE
                   SET stock_quantity = EXCLUDED.stock_quantity, updated_at = CURRENT_TIMESTAMP''',
                id=product_id, size=size, qty=qty)
        if sizes:
            keep = list(sizes)
            placeholders = ', '.join(f':s{i}' for i in range(len(keep)))
            execute(f'DELETE FROM product_sizes WHERE product_id = :id AND size NOT IN ({placeholders})',
                    id=product_id, **{f's{i}': s for i, s in enumerate(keep)})
        else:
            execute('DELETE FROM product_sizes WHERE product_id = :id', id=product_id)
        refresh_product_stock(product_id)

    if isinstance(data.get('specifications'), dict):
        values = pick(data['specifications'], SPEC_FIELDS)
        if values:
            existing = query_one('SELECT id FROM product_specifications WHERE product_id = :id', id=product_id)
            if existing:
                update_row('product_specifications', existing['id'], values)
            else:
                for required in ('welt_type', 'leather_type', 'sole_type', 'last_name'):
                    values.setdefault(required, '')
                insert_row('product_specifications', {'product_id': product_id, **values})


def _product_response(product_id, status=200, message=None):
    product = serialize_products(get_product_rows('p.id = :id', id=product_id))[0]
    body = {'product': product, 'product_id': product['id']}
    if message:
        body['message'] = message
    return jsonify(body), status


@admin_bp.route('/products', methods=['GET'])
def list_products():
    """All products, including hidden ones"""
    try:
        page, limit, offset = paging(default_limit=50, max_limit=200)
        search = request.args.get('search')
        clause, params = ('p.title ILIKE :s OR p.sku ILIKE :s', {'s': f'%{search}%'}) if search else ('true', {})
        rows = query_all(f'{PRODUCT_SELECT} WHERE {clause} ORDER BY p.created_at DESC LIMIT :limit OFFSET :offset',
                         limit=limit, offset=offset, **params)
        total = query_scalar(f'SELECT COUNT(*) FROM products p WHERE {clause}', **params)
        return jsonify({'products': serialize_products(rows), 'pagination': pagination(page, limit, total)}), 200

    except Exception as e:
        logger.error(f'List products error: {str(e)}')
        return error('Failed to fetch products', 500)


@admin_bp.route('/products', methods=['POST'])
def create_product():
    """Create a product with its images, sizes/stock and specifications"""
    try:
        data = json_body()
        title = clean_str(data.get('title'))
        if not title:
            return error('Title is required')
        try:
            price = float(data.get('price'))
        except (TypeError, ValueError):
            return error('A numeric price is required')
        if price <= 0:
            return error('Price must be greater than zero')

        category_id = _resolve_category(data)
        if not category_id:
            return error('A valid category or category_id is required')

        values = pick(data, PRODUCT_FIELDS)
        values.update({
            'title': title,
            'price': price,
            'category_id': category_id,
            'slug': unique_slug('products', data.get('slug') or title),
            'description': clean_str(data.get('description')),
        })
        values.setdefault('sku', f'HB-{slugify(title).upper()[:30]}-{str(query_scalar("SELECT gen_random_uuid()"))[:4].upper()}')
        if isinstance(data.get('in_stock'), bool) and not isinstance(data.get('sizes'), dict):
            values['in_stock'] = data['in_stock']

        product = insert_row('products', values)
        _save_product_children(product['id'], data)
        db.session.commit()
        return _product_response(product['id'], 201, 'Product created successfully')

    except (ValueError, TypeError) as e:
        db.session.rollback()
        return error(str(e))
    except IntegrityError:
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create product error: {str(e)}')
        return error('Failed to create product', 500)


@admin_bp.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        rows = get_product_rows('p.id = :id', id=product_id) if is_uuid(product_id) else []
        if not rows:
            return not_found('Product')
        return jsonify(serialize_products(rows)[0]), 200

    except Exception as e:
        logger.error(f'Get product error: {str(e)}')
        return error('Failed to fetch product', 500)


@admin_bp.route('/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    """Update a product; images/sizes/specifications are replaced only when included"""
    try:
        if not is_uuid(product_id) or not query_one('SELECT id FROM products WHERE id = :id', id=product_id):
            return not_found('Product')
        data = json_body()
        if not data:
            return error('No data provided')

        values = pick(data, PRODUCT_FIELDS)
        if 'price' in values:
            try:
                values['price'] = float(values['price'])
            except (TypeError, ValueError):
                return error('Price must be a number')
            if values['price'] <= 0:
                return error('Price must be greater than zero')
        if 'slug' in values:
            values['slug'] = unique_slug('products', values['slug'], exclude_id=product_id)
        category_id = _resolve_category(data)
        if category_id is None:
            return error('Category not found')
        if category_id:
            values['category_id'] = category_id
        if isinstance(data.get('in_stock'), bool) and not isinstance(data.get('sizes'), dict):
            values['in_stock'] = data['in_stock']

        update_row('products', product_id, values)
        _save_product_children(product_id, data)
        db.session.commit()
        return _product_response(product_id, 200, 'Product updated successfully')

    except (ValueError, TypeError) as e:
        db.session.rollback()
        return error(str(e))
    except IntegrityError:
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update product error: {str(e)}')
        return error('Failed to update product', 500)


@admin_bp.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Permanently delete a product. One that past orders refer to is hidden instead so order history stays intact."""
    try:
        if not is_uuid(product_id) or not query_one('SELECT id FROM products WHERE id = :id', id=product_id):
            return not_found('Product')

        if query_scalar('SELECT 1 FROM order_items WHERE product_id = :id LIMIT 1', id=product_id):
            execute('UPDATE products SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE id = :id', id=product_id)
            db.session.commit()
            return jsonify({
                'message': 'Product has existing orders, so it was hidden from the shop instead of deleted',
                'deleted': False,
            }), 200

        # images, sizes, specifications, reviews, wishlist and cart rows go with it (ON DELETE CASCADE)
        execute('DELETE FROM products WHERE id = :id', id=product_id)
        db.session.commit()
        return jsonify({'message': 'Product deleted successfully', 'deleted': True}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete product error: {str(e)}')
        return error('Failed to delete product', 500)


# ============================================================
# Orders
# ============================================================

@admin_bp.route('/orders', methods=['GET'])
def get_all_orders():
    """All orders, newest first (filter with ?status= and ?q=)"""
    try:
        page, limit, offset = paging(default_limit=20, max_limit=200)
        where, params = ['true'], {}

        status = request.args.get('status')
        if status:
            where.append('o.status = :status')
            params['status'] = status
        q = request.args.get('q')
        if q:
            where.append('(o.order_number ILIKE :q OR o.customer_name ILIKE :q OR o.customer_email ILIKE :q)')
            params['q'] = f'%{q}%'
        clause = ' AND '.join(where)

        rows = query_all(f'{ORDER_SELECT} WHERE {clause} ORDER BY o.created_at DESC LIMIT :limit OFFSET :offset',
                         limit=limit, offset=offset, **params)
        total = query_scalar(f'SELECT COUNT(*) FROM orders o WHERE {clause}', **params)
        return jsonify({'orders': serialize_orders(rows), 'pagination': pagination(page, limit, total)}), 200

    except Exception as e:
        logger.error(f'Get all orders error: {str(e)}')
        return error('Failed to fetch orders', 500)


def _order_or_none(order_ref):
    if is_uuid(order_ref):
        return query_one(f'{ORDER_SELECT} WHERE o.id = :id', id=order_ref)
    return None


@admin_bp.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    try:
        order = _order_or_none(order_id)
        if not order:
            return not_found('Order')
        return jsonify(serialize_orders([order])[0]), 200

    except Exception as e:
        logger.error(f'Admin get order error: {str(e)}')
        return error('Failed to fetch order', 500)


@admin_bp.route('/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Move an order along its lifecycle; the customer is notified and the timeline updated"""
    try:
        data = json_body()
        status = data.get('status')
        if status not in ORDER_STATUSES:
            return error(f'Invalid status. Valid options: {ORDER_STATUSES}')

        order = _order_or_none(order_id)
        if not order:
            return not_found('Order')
        if order['status'] == 'Cancelled' and status != 'Cancelled':
            return error('A cancelled order cannot be reopened. Ask the customer to place a new order.')

        changed = order['status'] != status
        set_order_status(order['id'], status, clean_str(data.get('location')) or None, clean_str(data.get('note')) or None)
        if status == 'Cancelled' and changed:
            restock_order(order['id'])
        if changed:
            notify_order_status(order, status)
        db.session.commit()

        updated = serialize_orders([_order_or_none(order_id)])[0]
        return jsonify({'message': 'Order status updated successfully', 'order': updated}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Update order status error: {str(e)}')
        return error('Failed to update order status', 500)


@admin_bp.route('/orders/<order_id>/payment', methods=['PUT'])
def update_payment_status(order_id):
    """Mark an order Paid / Pending / Refunded (there is no payment gateway attached yet)"""
    try:
        payment_status = json_body().get('payment_status')
        if payment_status not in PAYMENT_STATUSES:
            return error(f'Invalid payment status. Valid options: {PAYMENT_STATUSES}')

        order = _order_or_none(order_id)
        if not order:
            return not_found('Order')

        execute('UPDATE orders SET payment_status = :s, updated_at = CURRENT_TIMESTAMP WHERE id = :id',
                s=payment_status, id=order['id'])
        if order['payment_status'] != payment_status:
            add_notification(order['user_id'], f'Payment {payment_status}',
                             f'Payment for order {order["order_number"]} is now marked as {payment_status}.',
                             order_id=order['id'])
        db.session.commit()

        updated = serialize_orders([_order_or_none(order_id)])[0]
        return jsonify({'message': 'Payment status updated successfully', 'order': updated}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Update payment status error: {str(e)}')
        return error('Failed to update payment status', 500)


# ============================================================
# Users
# ============================================================

@admin_bp.route('/users', methods=['GET'])
def get_all_users():
    try:
        page, limit, offset = paging(default_limit=20, max_limit=200)
        q = request.args.get('q')
        clause, params = (
            ("(email ILIKE :q OR first_name ILIKE :q OR last_name ILIKE :q)", {'q': f'%{q}%'}) if q else ('true', {}))

        users = query_all(f'SELECT * FROM users WHERE {clause} ORDER BY created_at DESC LIMIT :limit OFFSET :offset',
                          limit=limit, offset=offset, **params)
        total = query_scalar(f'SELECT COUNT(*) FROM users WHERE {clause}', **params)
        stats = user_stats([u['id'] for u in users])

        return jsonify({
            'users': [serialize_user(u, stats.get(u['id'], {})) for u in users],
            'pagination': pagination(page, limit, total),
        }), 200

    except Exception as e:
        logger.error(f'Get all users error: {str(e)}')
        return error('Failed to fetch users', 500)


@admin_bp.route('/users/<user_id>/status', methods=['PUT'])
def toggle_user_status(user_id):
    """Suspend or reactivate a customer"""
    try:
        is_active = json_body().get('is_active')
        if not isinstance(is_active, bool):
            return error('is_active (true/false) is required')
        if not is_uuid(user_id):
            return not_found('User')
        if user_id == get_jwt_identity() and not is_active:
            return error('You cannot suspend your own account')

        result = execute('UPDATE users SET is_active = :a, updated_at = CURRENT_TIMESTAMP WHERE id = :id',
                         a=is_active, id=user_id)
        if result.rowcount == 0:
            db.session.rollback()
            return not_found('User')
        db.session.commit()
        return jsonify({'message': 'User status updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Toggle user status error: {str(e)}')
        return error('Failed to update user status', 500)


# ============================================================
# Coupons
# ============================================================

def _coupon_values(data, creating):
    """Accept both the API naming (discount_type/discount_value) and the frontend naming
    (discount_percent / discount_amount, min_spend, active)."""
    values = pick(data, {
        'description': ('description',), 'min_order_amount': ('min_spend', 'min_order_amount'),
        'max_discount_amount': ('max_discount_amount',), 'max_uses': ('max_uses',), 'is_active': ('active', 'is_active'),
    })
    if 'code' in data or creating:
        values['code'] = clean_str(data.get('code')).upper()
        if not values['code']:
            raise ValueError('Coupon code is required')

    if data.get('discount_percent') is not None:
        values['discount_type'], values['discount_value'] = 'percentage', data['discount_percent']
    elif data.get('discount_amount') is not None:
        values['discount_type'], values['discount_value'] = 'fixed', data['discount_amount']
    elif 'discount_value' in data or 'discount_type' in data or creating:
        values['discount_type'], values['discount_value'] = data.get('discount_type'), data.get('discount_value')

    if 'discount_value' in values or creating:
        if values.get('discount_type') not in ('percentage', 'fixed'):
            raise ValueError("discount_type must be 'percentage' or 'fixed'")
        try:
            value = float(values['discount_value'])
        except (TypeError, ValueError):
            raise ValueError('discount_value must be a number')
        if value <= 0 or (values['discount_type'] == 'percentage' and value > 100):
            raise ValueError('discount_value is out of range')
        values['discount_value'] = value

    if 'expires_at' in data:
        values['expires_at'] = parse_date(data['expires_at'])
    return values


@admin_bp.route('/coupons', methods=['GET'])
def list_coupons():
    try:
        rows = query_all('SELECT * FROM coupons ORDER BY created_at DESC')
        return jsonify({'coupons': [serialize_coupon(c) for c in rows]}), 200

    except Exception as e:
        logger.error(f'List coupons error: {str(e)}')
        return error('Failed to fetch coupons', 500)


@admin_bp.route('/coupons', methods=['POST'])
def create_coupon():
    try:
        values = _coupon_values(json_body(), creating=True)
        values['created_by'] = get_jwt_identity()
        coupon = insert_row('coupons', values)
        db.session.commit()
        return jsonify({'message': 'Coupon created successfully', 'coupon_id': str(coupon['id']),
                        'coupon': serialize_coupon(coupon)}), 201

    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    except IntegrityError:
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create coupon error: {str(e)}')
        return error('Failed to create coupon', 500)


@admin_bp.route('/coupons/<coupon_id>', methods=['PUT'])
def update_coupon(coupon_id):
    """Edit a coupon; send {"active": false} to switch it off"""
    try:
        if not is_uuid(coupon_id):
            return not_found('Coupon')
        values = _coupon_values(json_body(), creating=False)
        coupon = update_row('coupons', coupon_id, values)
        if not coupon:
            return not_found('Coupon')
        db.session.commit()
        return jsonify({'message': 'Coupon updated successfully', 'coupon': serialize_coupon(coupon)}), 200

    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    except IntegrityError:
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update coupon error: {str(e)}')
        return error('Failed to update coupon', 500)


@admin_bp.route('/coupons/<coupon_id>', methods=['DELETE'])
def delete_coupon(coupon_id):
    try:
        if not is_uuid(coupon_id):
            return not_found('Coupon')
        # Orders keep coupon_code as text, so history survives
        execute('UPDATE orders SET coupon_id = NULL WHERE coupon_id = :id', id=coupon_id)
        result = execute('DELETE FROM coupons WHERE id = :id', id=coupon_id)
        if result.rowcount == 0:
            db.session.rollback()
            return not_found('Coupon')
        db.session.commit()
        return jsonify({'message': 'Coupon deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete coupon error: {str(e)}')
        return error('Failed to delete coupon', 500)


# ============================================================
# Banners
# ============================================================

BANNER_FIELDS = {
    'title': ('title',), 'subtitle': ('subtitle',), 'badge': ('badge',), 'button_text': ('button_text',),
    'link_url': ('link', 'link_url'), 'image_url': ('image_url',), 'is_active': ('active', 'is_active'),
    'background_color': ('background_color',), 'display_order': ('display_order',),
}


def _banner_values(data):
    values = pick(data, BANNER_FIELDS)
    for column, key in (('start_date', 'start_date'), ('end_date', 'end_date')):
        if key in data:
            values[column] = parse_date(data[key])
    return values


@admin_bp.route('/banners', methods=['GET'])
def list_banners():
    try:
        rows = query_all('SELECT * FROM promotional_banners ORDER BY display_order, created_at DESC')
        return jsonify({'banners': [serialize_banner(b) for b in rows]}), 200

    except Exception as e:
        logger.error(f'List banners error: {str(e)}')
        return error('Failed to fetch banners', 500)


@admin_bp.route('/banners', methods=['POST'])
def create_banner():
    try:
        values = _banner_values(json_body())
        if not clean_str(values.get('title')) or not clean_str(values.get('image_url')):
            return error('title and image_url are required')
        values['created_by'] = get_jwt_identity()
        banner = insert_row('promotional_banners', values)
        db.session.commit()
        return jsonify({'message': 'Banner created successfully', 'banner': serialize_banner(banner)}), 201

    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create banner error: {str(e)}')
        return error('Failed to create banner', 500)


@admin_bp.route('/banners/<banner_id>', methods=['PUT'])
def update_banner(banner_id):
    try:
        if not is_uuid(banner_id):
            return not_found('Banner')
        banner = update_row('promotional_banners', banner_id, _banner_values(json_body()))
        if not banner:
            return not_found('Banner')
        db.session.commit()
        return jsonify({'message': 'Banner updated successfully', 'banner': serialize_banner(banner)}), 200

    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update banner error: {str(e)}')
        return error('Failed to update banner', 500)


@admin_bp.route('/banners/<banner_id>', methods=['DELETE'])
def delete_banner(banner_id):
    try:
        if not is_uuid(banner_id):
            return not_found('Banner')
        result = execute('DELETE FROM promotional_banners WHERE id = :id', id=banner_id)
        if result.rowcount == 0:
            db.session.rollback()
            return not_found('Banner')
        db.session.commit()
        return jsonify({'message': 'Banner deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete banner error: {str(e)}')
        return error('Failed to delete banner', 500)


# ============================================================
# Reviews (moderation)
# ============================================================

REVIEW_SELECT = 'SELECT r.*, p.title AS product_title FROM product_reviews r JOIN products p ON p.id = r.product_id'


@admin_bp.route('/reviews', methods=['GET'])
def list_reviews():
    try:
        page, limit, offset = paging(default_limit=50, max_limit=200)
        status = request.args.get('status')
        clause, params = ('r.status = :status', {'status': status}) if status else ('true', {})
        rows = query_all(f'{REVIEW_SELECT} WHERE {clause} ORDER BY r.created_at DESC LIMIT :limit OFFSET :offset',
                         limit=limit, offset=offset, **params)
        total = query_scalar(f'SELECT COUNT(*) FROM product_reviews r WHERE {clause}', **params)
        return jsonify({'reviews': [serialize_review(r) for r in rows],
                        'pagination': pagination(page, limit, total)}), 200

    except Exception as e:
        logger.error(f'List reviews error: {str(e)}')
        return error('Failed to fetch reviews', 500)


@admin_bp.route('/reviews/<review_id>/status', methods=['PUT'])
def update_review_status(review_id):
    """Approve, reject or re-queue a review; the product rating is recomputed from approved reviews"""
    try:
        status = json_body().get('status')
        if status not in ('Approved', 'Pending', 'Rejected'):
            return error("status must be 'Approved', 'Pending' or 'Rejected'")
        if not is_uuid(review_id):
            return not_found('Review')

        review = query_one(
            '''UPDATE product_reviews SET status = :status, is_approved = :approved, updated_at = CURRENT_TIMESTAMP
               WHERE id = :id RETURNING product_id''', status=status, approved=(status == 'Approved'), id=review_id)
        if not review:
            return not_found('Review')
        refresh_product_rating(review['product_id'])
        db.session.commit()
        return jsonify({'message': 'Review status updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Update review status error: {str(e)}')
        return error('Failed to update review', 500)


@admin_bp.route('/reviews/<review_id>', methods=['DELETE'])
def delete_review(review_id):
    try:
        if not is_uuid(review_id):
            return not_found('Review')
        review = query_one('DELETE FROM product_reviews WHERE id = :id RETURNING product_id', id=review_id)
        if not review:
            return not_found('Review')
        refresh_product_rating(review['product_id'])
        db.session.commit()
        return jsonify({'message': 'Review deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete review error: {str(e)}')
        return error('Failed to delete review', 500)


# ============================================================
# Blog
# ============================================================

BLOG_FIELDS = {
    'title': ('title',), 'content': ('content',), 'excerpt': ('excerpt',), 'category': ('category',),
    'featured_image_url': ('image', 'featured_image_url'), 'author_name': ('author', 'author_name'),
    'author_role': ('author_role',), 'read_time': ('read_time',), 'is_published': ('is_published',),
}


@admin_bp.route('/blog', methods=['GET'])
def list_blog_posts():
    try:
        rows = query_all(f'{BLOG_SELECT} ORDER BY b.created_at DESC')
        return jsonify({'posts': [serialize_blog_post(p) for p in rows]}), 200

    except Exception as e:
        logger.error(f'List blog posts error: {str(e)}')
        return error('Failed to fetch blog posts', 500)


def _blog_response(post_id, status, message):
    post = query_one(f'{BLOG_SELECT} WHERE b.id = :id', id=post_id)
    return jsonify({'message': message, 'post': serialize_blog_post(post)}), status


@admin_bp.route('/blog', methods=['POST'])
def create_blog_post():
    try:
        data = json_body()
        values = pick(data, BLOG_FIELDS)
        if not clean_str(values.get('title')) or not clean_str(values.get('content')):
            return error('title and content are required')
        values['slug'] = unique_slug('blog_posts', data.get('slug') or values['title'])
        values.setdefault('is_published', True)
        if values['is_published']:
            values['published_at'] = parse_date(data.get('publish_date')) or datetime.utcnow()
        values['author_id'] = get_jwt_identity()
        post = insert_row('blog_posts', values)
        db.session.commit()
        return _blog_response(post['id'], 201, 'Blog post created successfully')

    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    except IntegrityError:
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create blog post error: {str(e)}')
        return error('Failed to create blog post', 500)


@admin_bp.route('/blog/<post_id>', methods=['PUT'])
def update_blog_post(post_id):
    try:
        if not is_uuid(post_id):
            return not_found('Blog post')
        data = json_body()
        values = pick(data, BLOG_FIELDS)
        if 'slug' in data:
            values['slug'] = unique_slug('blog_posts', data['slug'], exclude_id=post_id)
        if 'publish_date' in data:
            values['published_at'] = parse_date(data['publish_date'])
        if values.get('is_published') and 'published_at' not in values:
            values['published_at'] = datetime.utcnow()
        if not update_row('blog_posts', post_id, values):
            return not_found('Blog post')
        db.session.commit()
        return _blog_response(post_id, 200, 'Blog post updated successfully')

    except ValueError as e:
        db.session.rollback()
        return error(str(e))
    except IntegrityError:
        raise
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update blog post error: {str(e)}')
        return error('Failed to update blog post', 500)


@admin_bp.route('/blog/<post_id>', methods=['DELETE'])
def delete_blog_post(post_id):
    try:
        if not is_uuid(post_id):
            return not_found('Blog post')
        result = execute('DELETE FROM blog_posts WHERE id = :id', id=post_id)
        if result.rowcount == 0:
            db.session.rollback()
            return not_found('Blog post')
        db.session.commit()
        return jsonify({'message': 'Blog post deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete blog post error: {str(e)}')
        return error('Failed to delete blog post', 500)


# ============================================================
# Stores
# ============================================================

STORE_FIELDS = {
    'name': ('name',), 'street_address': ('street', 'street_address', 'address'), 'city': ('city',),
    'state': ('state',), 'postal_code': ('postal_code',), 'country': ('country',), 'phone': ('phone',),
    'email': ('email',), 'hours_text': ('hours',), 'image_url': ('image',), 'description': ('description',),
    'appointment_available': ('appointment_available',), 'services': ('services',), 'is_active': ('is_active',),
}


def _store_values(data, creating):
    values = pick(data, STORE_FIELDS)
    coords = data.get('coordinates')
    if isinstance(coords, dict):
        values['latitude'], values['longitude'] = coords.get('lat'), coords.get('lng')
    if creating:
        for column in ('state', 'postal_code', 'country'):
            values.setdefault(column, '')
    return values


def _store_response(store_id, status, message):
    store = query_one('SELECT * FROM store_locations WHERE id = :id', id=store_id)
    hours = store_hours_by_day([store['id']]).get(store['id'])
    return jsonify({'message': message, 'store': serialize_store(store, hours)}), status


@admin_bp.route('/stores', methods=['GET'])
def list_stores():
    try:
        rows = query_all('SELECT * FROM store_locations ORDER BY city, name')
        hours = store_hours_by_day([r['id'] for r in rows])
        return jsonify({'stores': [serialize_store(r, hours.get(r['id'])) for r in rows]}), 200

    except Exception as e:
        logger.error(f'List stores error: {str(e)}')
        return error('Failed to fetch stores', 500)


@admin_bp.route('/stores', methods=['POST'])
def create_store():
    try:
        values = _store_values(json_body(), creating=True)
        if not all(clean_str(values.get(f)) for f in ('name', 'street_address', 'city')):
            return error('name, address and city are required')
        store = insert_row('store_locations', values)
        db.session.commit()
        return _store_response(store['id'], 201, 'Store created successfully')

    except Exception as e:
        db.session.rollback()
        logger.error(f'Create store error: {str(e)}')
        return error('Failed to create store', 500)


@admin_bp.route('/stores/<store_id>', methods=['PUT'])
def update_store(store_id):
    try:
        if not is_uuid(store_id):
            return not_found('Store')
        if not update_row('store_locations', store_id, _store_values(json_body(), creating=False)):
            return not_found('Store')
        db.session.commit()
        return _store_response(store_id, 200, 'Store updated successfully')

    except Exception as e:
        db.session.rollback()
        logger.error(f'Update store error: {str(e)}')
        return error('Failed to update store', 500)


@admin_bp.route('/stores/<store_id>', methods=['DELETE'])
def delete_store(store_id):
    try:
        if not is_uuid(store_id):
            return not_found('Store')
        result = execute('DELETE FROM store_locations WHERE id = :id', id=store_id)
        if result.rowcount == 0:
            db.session.rollback()
            return not_found('Store')
        db.session.commit()
        return jsonify({'message': 'Store deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete store error: {str(e)}')
        return error('Failed to delete store', 500)


# ============================================================
# Site content & contact messages
# ============================================================

@admin_bp.route('/site-content', methods=['PUT'])
def save_site_content():
    """Store the whole SiteContent object edited in the admin CMS"""
    try:
        content = json_body().get('content')
        if not isinstance(content, dict):
            return error('content must be an object')
        execute(
            '''INSERT INTO site_settings (key, value) VALUES ('site_content', CAST(:value AS jsonb))
               ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP''',
            value=json.dumps(content))
        db.session.commit()
        return jsonify({'message': 'Site content saved'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Save site content error: {str(e)}')
        return error('Failed to save site content', 500)


@admin_bp.route('/site-content', methods=['DELETE'])
def reset_site_content():
    """Drop the saved content so the frontend falls back to its defaults"""
    try:
        execute("DELETE FROM site_settings WHERE key = 'site_content'")
        db.session.commit()
        return jsonify({'message': 'Site content reset'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Reset site content error: {str(e)}')
        return error('Failed to reset site content', 500)


@admin_bp.route('/messages', methods=['GET'])
def list_messages():
    try:
        page, limit, offset = paging(default_limit=50, max_limit=200)
        rows = query_all('SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT :limit OFFSET :offset',
                         limit=limit, offset=offset)
        total = query_scalar('SELECT COUNT(*) FROM contact_messages')
        return jsonify({
            'messages': [{
                'id': str(m['id']), 'name': m['name'], 'email': m['email'], 'subject': m['subject'],
                'message': m['message'], 'is_read': bool(m['is_read']), 'created_at': m['created_at'].isoformat(),
            } for m in rows],
            'pagination': pagination(page, limit, total),
        }), 200

    except Exception as e:
        logger.error(f'List messages error: {str(e)}')
        return error('Failed to fetch messages', 500)


@admin_bp.route('/messages/<message_id>/read', methods=['POST'])
def mark_message_read(message_id):
    try:
        if not is_uuid(message_id):
            return not_found('Message')
        result = execute('UPDATE contact_messages SET is_read = true WHERE id = :id', id=message_id)
        if result.rowcount == 0:
            db.session.rollback()
            return not_found('Message')
        db.session.commit()
        return jsonify({'message': 'Message marked as read'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Mark message read error: {str(e)}')
        return error('Failed to update message', 500)
