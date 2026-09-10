from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from sqlalchemy import text
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)
orders_bp = Blueprint('orders', __name__)

# ============================================================
# Orders Endpoints
# ============================================================

@orders_bp.route('', methods=['POST'])
def create_order():
    """Create new order"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('customer_email') or not data.get('items'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        customer_email = data.get('customer_email', '').strip().lower()
        customer_name = data.get('customer_name', '').strip()
        customer_phone = data.get('customer_phone', '').strip()
        items = data.get('items', [])
        subtotal = data.get('subtotal', 0)
        tax = data.get('tax', 0)
        shipping_cost = data.get('shipping_cost', 0)
        discount_amount = data.get('discount_amount', 0)
        coupon_id = data.get('coupon_id')
        shipping_address = data.get('shipping_address', {})
        payment_method = data.get('payment_method', 'credit_card')
        
        if not items or not isinstance(items, list):
            return jsonify({'error': 'Items must be a non-empty list'}), 400
        
        if not subtotal or subtotal <= 0:
            return jsonify({'error': 'Invalid subtotal'}), 400
        
        # Generate order number
        order_number = f'ORD-{datetime.now().strftime("%Y%m%d")}-{str(uuid.uuid4())[:8].upper()}'
        total = subtotal + tax + shipping_cost - discount_amount
        
        # Get user ID if logged in
        user_id = None
        try:
            user_id = get_jwt_identity()
        except:
            pass
        
        # Create order
        order_id = uuid.uuid4()
        
        db.session.execute(
            text('''
                INSERT INTO orders (
                    id, order_number, user_id, customer_name, customer_email,
                    customer_phone, subtotal, tax, shipping_cost, discount_amount,
                    coupon_id, total, status, payment_method, payment_status, created_at, updated_at
                ) VALUES (
                    :id, :order_number, :user_id, :customer_name, :customer_email,
                    :customer_phone, :subtotal, :tax, :shipping_cost, :discount_amount,
                    :coupon_id, :total, :status, :payment_method, :payment_status, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            '''),
            {
                'id': str(order_id),
                'order_number': order_number,
                'user_id': user_id,
                'customer_name': customer_name,
                'customer_email': customer_email,
                'customer_phone': customer_phone,
                'subtotal': subtotal,
                'tax': tax,
                'shipping_cost': shipping_cost,
                'discount_amount': discount_amount,
                'coupon_id': coupon_id,
                'total': total,
                'status': 'Pending',
                'payment_method': payment_method,
                'payment_status': 'Pending'
            }
        )
        
        # Add order items
        for item in items:
            item_id = uuid.uuid4()
            db.session.execute(
                text('''
                    INSERT INTO order_items (
                        id, order_id, product_id, product_title, size,
                        quantity, unit_price, subtotal, created_at
                    ) VALUES (
                        :id, :order_id, :product_id, :product_title, :size,
                        :quantity, :unit_price, :subtotal, CURRENT_TIMESTAMP
                    )
                '''),
                {
                    'id': str(item_id),
                    'order_id': str(order_id),
                    'product_id': item.get('product_id'),
                    'product_title': item.get('product_title', 'Unknown'),
                    'size': item.get('size', ''),
                    'quantity': item.get('quantity', 1),
                    'unit_price': item.get('price', 0),
                    'subtotal': item.get('quantity', 1) * item.get('price', 0)
                }
            )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': {
                'id': str(order_id),
                'order_number': order_number,
                'total': float(total),
                'status': 'Pending',
                'payment_status': 'Pending'
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create order error: {str(e)}')
        return jsonify({'error': 'Failed to create order'}), 500


@orders_bp.route('', methods=['GET'])
@jwt_required()
def get_user_orders():
    """Get user's order history"""
    try:
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        offset = (page - 1) * limit
        
        orders = db.session.execute(
            text('''
                SELECT id, order_number, total, status, payment_status, created_at
                FROM orders
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            '''),
            {'user_id': user_id, 'limit': limit, 'offset': offset}
        ).fetchall()
        
        # Get total count
        total = db.session.execute(
            text('SELECT COUNT(*) FROM orders WHERE user_id = :user_id'),
            {'user_id': user_id}
        ).scalar()
        
        orders_list = [
            {
                'id': str(o[0]),
                'order_number': o[1],
                'total': float(o[2]),
                'status': o[3],
                'payment_status': o[4],
                'created_at': str(o[5])
            } for o in orders
        ]
        
        return jsonify({
            'orders': orders_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Get orders error: {str(e)}')
        return jsonify({'error': 'Failed to fetch orders'}), 500


@orders_bp.route('/<order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    """Get order details"""
    try:
        user_id = get_jwt_identity()
        
        # Get order
        order = db.session.execute(
            text('''
                SELECT id, order_number, customer_name, customer_email, customer_phone,
                       subtotal, tax, shipping_cost, discount_amount, total, status,
                       payment_method, payment_status, tracking_number, created_at
                FROM orders
                WHERE id = :id AND user_id = :user_id
            '''),
            {'id': order_id, 'user_id': user_id}
        ).fetchone()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Get order items
        items = db.session.execute(
            text('''
                SELECT id, product_id, product_title, size, quantity, unit_price, subtotal
                FROM order_items
                WHERE order_id = :order_id
            '''),
            {'order_id': order_id}
        ).fetchall()
        
        order_data = {
            'id': str(order[0]),
            'order_number': order[1],
            'customer_name': order[2],
            'customer_email': order[3],
            'customer_phone': order[4],
            'subtotal': float(order[5]),
            'tax': float(order[6]),
            'shipping_cost': float(order[7]),
            'discount_amount': float(order[8]),
            'total': float(order[9]),
            'status': order[10],
            'payment_method': order[11],
            'payment_status': order[12],
            'tracking_number': order[13],
            'items': [
                {
                    'id': str(item[0]),
                    'product_id': str(item[1]),
                    'title': item[2],
                    'size': item[3],
                    'quantity': item[4],
                    'unit_price': float(item[5]),
                    'subtotal': float(item[6])
                } for item in items
            ],
            'created_at': str(order[14])
        }
        
        return jsonify(order_data), 200
        
    except Exception as e:
        logger.error(f'Get order error: {str(e)}')
        return jsonify({'error': 'Failed to fetch order'}), 500


@orders_bp.route('/<order_id>/track', methods=['GET'])
def track_order(order_id):
    """Track order status"""
    try:
        order = db.session.execute(
            text('''
                SELECT order_number, status, payment_status, tracking_number, updated_at
                FROM orders
                WHERE id = :id
            '''),
            {'id': order_id}
        ).fetchone()
        
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        tracking_info = {
            'order_number': order[0],
            'status': order[1],
            'payment_status': order[2],
            'tracking_number': order[3],
            'updated_at': str(order[4]),
            'estimated_delivery': 'N/A'  # TODO: Calculate based on shipping method
        }
        
        return jsonify(tracking_info), 200
        
    except Exception as e:
        logger.error(f'Track order error: {str(e)}')
        return jsonify({'error': 'Failed to track order'}), 500
