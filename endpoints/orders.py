from decimal import Decimal
import json
import logging

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from services import (
    CUSTOMER_CANCELLABLE, ORDER_SELECT, add_notification, evaluate_coupon, generate_order_number,
    generate_tracking_number, init_tracking_logs, notify_admins, notify_order_status, refresh_product_stock,
    restock_order, serialize_address, serialize_orders, set_order_status, shipping_for,
)
from utils import (
    clean_str, error, execute, is_admin_user, is_uuid, json_body, money, optional_user_id, pagination,
    paging, query_all, query_one, query_scalar,
)

logger = logging.getLogger(__name__)
orders_bp = Blueprint('orders', __name__)

DEFAULT_DELIVERY = {'id': 'del-express', 'name': 'Courier Partner', 'estimated_days': '3-5 Business Days'}


class OrderError(Exception):
    """A problem with the submitted order that the customer can fix."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def find_order(ref):
    """Look an order up by its id or its order number (e.g. HB-2026-98124)."""
    if is_uuid(ref):
        return query_one(f'{ORDER_SELECT} WHERE o.id = :ref', ref=ref)
    return query_one(f'{ORDER_SELECT} WHERE LOWER(o.order_number) = LOWER(:ref)', ref=str(ref).strip())


def _resolve_shipping_address(data, user_id):
    address_id = data.get('shipping_address_id')
    if address_id:
        if not user_id or not is_uuid(address_id):
            raise OrderError('Shipping address not found', 404)
        row = query_one('SELECT * FROM addresses WHERE id = :id AND user_id = :user_id', id=address_id, user_id=user_id)
        if not row:
            raise OrderError('Shipping address not found', 404)
        return serialize_address(row)

    raw = data.get('shipping_address')
    if not isinstance(raw, dict):
        raise OrderError('A shipping address is required')
    address = {
        'full_name': clean_str(raw.get('full_name') or raw.get('fullName')),
        'phone': clean_str(raw.get('phone')),
        'street': clean_str(raw.get('street') or raw.get('street_address')),
        'apartment': clean_str(raw.get('apartment')),
        'city': clean_str(raw.get('city')),
        'state': clean_str(raw.get('state')),
        'postal_code': clean_str(raw.get('postal_code') or raw.get('postalCode')),
        'country': clean_str(raw.get('country')),
        'address_type': clean_str(raw.get('address_type') or raw.get('addressType')) or 'Home',
    }
    missing = [k for k in ('full_name', 'phone', 'street', 'city', 'postal_code', 'country') if not address[k]]
    if missing:
        raise OrderError(f'Shipping address is missing: {", ".join(missing)}')
    return address


def _reserve_items(raw_items):
    """Validate the cart against the catalogue, reserve stock and price every line.

    Prices always come from the database, never from the client.
    """
    if not isinstance(raw_items, list) or not raw_items:
        raise OrderError('Items must be a non-empty list')

    wanted = {}
    for item in raw_items:
        if not isinstance(item, dict):
            raise OrderError('Invalid item')
        product_id = str(item.get('product_id') or item.get('shoe_id') or '')
        size = clean_str(item.get('size'))
        quantity = item.get('quantity', 1)
        if not is_uuid(product_id) or not size:
            raise OrderError('Each item needs a product_id and a size')
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 20:
            raise OrderError('Quantity must be a whole number between 1 and 20')
        key = (product_id, size)
        wanted[key] = wanted.get(key, 0) + quantity

    lines = []
    # Lock rows in a stable order so concurrent checkouts cannot deadlock
    for (product_id, size), quantity in sorted(wanted.items()):
        row = query_one(
            '''SELECT p.id, p.title, p.price, p.is_active, ps.stock_quantity
               FROM products p JOIN product_sizes ps ON ps.product_id = p.id
               WHERE p.id = :id AND ps.size = :size FOR UPDATE OF ps''',
            id=product_id, size=size)
        if not row or not row['is_active']:
            raise OrderError(f'Product or size no longer available ({size})', 404)
        if row['stock_quantity'] < quantity:
            raise OrderError(f'Only {row["stock_quantity"]} left in {size} for "{row["title"]}"', 409)
        execute(
            '''UPDATE product_sizes SET stock_quantity = stock_quantity - :qty, updated_at = CURRENT_TIMESTAMP
               WHERE product_id = :id AND size = :size''', qty=quantity, id=product_id, size=size)
        lines.append({
            'product_id': product_id, 'title': row['title'], 'size': size,
            'quantity': quantity, 'unit_price': row['price'], 'subtotal': row['price'] * quantity,
        })
    for product_id in {line['product_id'] for line in lines}:
        refresh_product_stock(product_id)
    return lines


# ============================================================
# Orders Endpoints
# ============================================================

@orders_bp.route('', methods=['POST'])
def create_order():
    """Create a new order (guests may order too; a token links it to the account)"""
    try:
        data = json_body()
        user_id = optional_user_id()

        user = query_one('SELECT * FROM users WHERE id = :id AND is_active = true', id=user_id) if user_id else None
        address = _resolve_shipping_address(data, user_id)

        customer_name = clean_str(data.get('customer_name')) or (
            f'{user["first_name"]} {user["last_name"]}'.strip() if user else address['full_name'])
        customer_email = (clean_str(data.get('customer_email')) or (user['email'] if user else '')).lower()
        customer_phone = clean_str(data.get('customer_phone')) or (user['phone'] if user and user['phone'] else address['phone'])
        if not customer_email:
            raise OrderError('customer_email is required')

        lines = _reserve_items(data.get('items'))
        subtotal = sum((line['subtotal'] for line in lines), Decimal('0'))

        coupon, discount, coupon_error = None, Decimal('0'), None
        coupon_code = clean_str(data.get('coupon_code'))
        if coupon_code:
            coupon, discount, coupon_error = evaluate_coupon(coupon_code, subtotal)
            if coupon_error:
                raise OrderError(coupon_error)
            claimed = execute(
                '''UPDATE coupons SET used_count = used_count + 1, updated_at = CURRENT_TIMESTAMP
                   WHERE id = :id AND (max_uses IS NULL OR used_count < max_uses)''', id=coupon['id'])
            if claimed.rowcount == 0:
                raise OrderError('Coupon usage limit reached')

        shipping = shipping_for(subtotal)
        total = money(subtotal - discount + shipping)

        requested = data.get('delivery_method') if isinstance(data.get('delivery_method'), dict) else {}
        delivery = {
            'id': clean_str(requested.get('id')) or DEFAULT_DELIVERY['id'],
            'name': clean_str(requested.get('name')) or DEFAULT_DELIVERY['name'],
            'price': float(shipping),
            'estimated_days': clean_str(requested.get('estimated_days') or requested.get('estimatedDays'))
            or DEFAULT_DELIVERY['estimated_days'],
        }

        order_number = generate_order_number()
        order = query_one(
            '''INSERT INTO orders (
                   order_number, user_id, customer_name, customer_email, customer_phone,
                   subtotal, tax, shipping_cost, discount_amount, coupon_id, coupon_code, total,
                   status, payment_method, payment_status, shipping_address_id, shipping_address,
                   delivery_method, estimated_delivery_date, tracking_number, courier, notes
               ) VALUES (
                   :order_number, :user_id, :customer_name, :customer_email, :customer_phone,
                   :subtotal, 0, :shipping, :discount, :coupon_id, :coupon_code, :total,
                   'Placed', :payment_method, 'Pending', :address_id, CAST(:address AS jsonb),
                   CAST(:delivery AS jsonb), :eta, :tracking_number, :courier, :notes
               ) RETURNING id''',
            order_number=order_number, user_id=user_id, customer_name=customer_name,
            customer_email=customer_email, customer_phone=customer_phone,
            subtotal=subtotal, shipping=shipping, discount=discount,
            coupon_id=coupon['id'] if coupon else None, coupon_code=coupon['code'] if coupon else None,
            total=total, payment_method=clean_str(data.get('payment_method'))[:100] or None,
            address_id=data.get('shipping_address_id') or None, address=json.dumps(address),
            delivery=json.dumps(delivery), eta=delivery['estimated_days'],
            tracking_number=generate_tracking_number(), courier=delivery['name'],
            notes=clean_str(data.get('special_instructions')) or None,
        )
        order_id = order['id']

        for line in lines:
            execute(
                '''INSERT INTO order_items (order_id, product_id, product_title, size, quantity, unit_price, subtotal)
                   VALUES (:order_id, :product_id, :title, :size, :quantity, :unit_price, :subtotal)''',
                order_id=order_id, **line)

        init_tracking_logs(order_id, address['city'])
        add_notification(
            user_id, 'Order Placed Successfully',
            f'Order {order_number} has been placed. You will be notified when the workshop accepts it.',
            order_id=order_id)
        notify_admins(
            'New Order Received',
            f'{customer_name} placed order {order_number} worth ${total} ({data.get("payment_method") or "payment pending"}).',
            order_id=order_id)

        db.session.commit()

        created = serialize_orders(query_all(f'{ORDER_SELECT} WHERE o.id = :id', id=order_id))[0]
        return jsonify({'message': 'Order created successfully', 'order': created}), 201

    except OrderError as e:
        db.session.rollback()
        return error(e.message, e.status)
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create order error: {str(e)}')
        return error('Failed to create order', 500)


@orders_bp.route('', methods=['GET'])
@jwt_required()
def get_user_orders():
    """Get the logged-in user's order history"""
    try:
        user_id = get_jwt_identity()
        page, limit, offset = paging()

        rows = query_all(
            f'{ORDER_SELECT} WHERE o.user_id = :user_id ORDER BY o.created_at DESC LIMIT :limit OFFSET :offset',
            user_id=user_id, limit=limit, offset=offset)
        total = query_scalar('SELECT COUNT(*) FROM orders WHERE user_id = :user_id', user_id=user_id)

        return jsonify({
            'orders': serialize_orders(rows),
            'pagination': pagination(page, limit, total),
        }), 200

    except Exception as e:
        logger.error(f'Get orders error: {str(e)}')
        return error('Failed to fetch orders', 500)


@orders_bp.route('/<order_ref>', methods=['GET'])
@jwt_required()
def get_order(order_ref):
    """Get order details (by id or order number) for the owner or an admin"""
    try:
        user_id = get_jwt_identity()
        order = find_order(order_ref)
        if not order or (str(order['user_id']) != str(user_id) and not is_admin_user(user_id)):
            return error('Order not found', 404)
        return jsonify(serialize_orders([order])[0]), 200

    except Exception as e:
        logger.error(f'Get order error: {str(e)}')
        return error('Failed to fetch order', 500)


@orders_bp.route('/<order_ref>/track', methods=['GET'])
def track_order(order_ref):
    """Public order tracking by order id or order number (no personal details are returned)"""
    try:
        order = find_order(order_ref)
        if not order:
            return error('Order not found', 404)

        full = serialize_orders([order])[0]
        address = full['shipping_address'] or {}
        return jsonify({
            'id': full['id'],
            'order_number': full['order_number'],
            'status': full['status'],
            'payment_status': full['payment_status'],
            'tracking_number': full['tracking_number'],
            'courier': full['courier'],
            'estimated_delivery_date': full['estimated_delivery_date'],
            'created_at': full['created_at'],
            'updated_at': full['updated_at'],
            'destination_city': address.get('city'),
            'items': [
                {k: i[k] for k in ('title', 'image', 'size', 'quantity')} for i in full['items']
            ],
            'tracking_logs': full['tracking_logs'],
        }), 200

    except Exception as e:
        logger.error(f'Track order error: {str(e)}')
        return error('Failed to track order', 500)


@orders_bp.route('/<order_ref>/cancel', methods=['POST'])
@jwt_required()
def cancel_order(order_ref):
    """Cancel an order before it ships"""
    try:
        user_id = get_jwt_identity()
        order = find_order(order_ref)
        if not order or str(order['user_id']) != str(user_id):
            return error('Order not found', 404)
        if order['status'] not in CUSTOMER_CANCELLABLE:
            return error(f'Orders that are {order["status"]} can no longer be cancelled. Please contact support.')

        set_order_status(order['id'], 'Cancelled')
        restock_order(order['id'])
        notify_order_status(order, 'Cancelled')
        notify_admins('Order Cancelled', f'{order["customer_name"]} cancelled order {order["order_number"]}.',
                      order_id=order['id'])
        db.session.commit()

        updated = serialize_orders(query_all(f'{ORDER_SELECT} WHERE o.id = :id', id=order['id']))[0]
        return jsonify({'message': 'Order cancelled', 'order': updated}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Cancel order error: {str(e)}')
        return error('Failed to cancel order', 500)
