from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from sqlalchemy import text
import logging
import uuid

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

# ============================================================
# Admin Dashboard Endpoints
# ============================================================

@admin_bp.before_request
@jwt_required()
def check_admin():
    """Check if user is admin"""
    user_id = get_jwt_identity()
    
    is_admin = db.session.execute(
        text('SELECT is_admin FROM users WHERE id = :id'),
        {'id': user_id}
    ).scalar()
    
    if not is_admin:
        return jsonify({'error': 'Unauthorized - Admin access required'}), 403


@admin_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """Get admin dashboard statistics"""
    try:
        stats = {
            'total_users': db.session.execute(text('SELECT COUNT(*) FROM users')).scalar(),
            'total_orders': db.session.execute(text('SELECT COUNT(*) FROM orders')).scalar(),
            'total_products': db.session.execute(text('SELECT COUNT(*) FROM products WHERE is_active = true')).scalar(),
            'total_revenue': float(db.session.execute(text('SELECT COALESCE(SUM(total), 0) FROM orders WHERE status = \'Completed\'')).scalar() or 0),
            'pending_orders': db.session.execute(text('SELECT COUNT(*) FROM orders WHERE status = \'Pending\'')).scalar()
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f'Dashboard error: {str(e)}')
        return jsonify({'error': 'Failed to fetch dashboard'}), 500


# ============================================================
# Products Management
# ============================================================

@admin_bp.route('/products', methods=['POST'])
def create_product():
    """Create new product"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['title', 'price', 'category_id']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        product_id = uuid.uuid4()
        
        db.session.execute(
            text('''
                INSERT INTO products (
                    id, title, slug, sku, category_id, price, original_price,
                    short_description, description, color, is_active, created_at
                ) VALUES (
                    :id, :title, :slug, :sku, :category_id, :price, :original_price,
                    :short_description, :description, :color, true, CURRENT_TIMESTAMP
                )
            '''),
            {
                'id': str(product_id),
                'title': data['title'],
                'slug': data.get('slug', data['title'].lower().replace(' ', '-')),
                'sku': data.get('sku', str(product_id)[:8]),
                'category_id': data['category_id'],
                'price': data['price'],
                'original_price': data.get('original_price'),
                'short_description': data.get('short_description', ''),
                'description': data.get('description', ''),
                'color': data.get('color', '')
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product_id': str(product_id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create product error: {str(e)}')
        return jsonify({'error': 'Failed to create product'}), 500


@admin_bp.route('/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    """Update product"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        updates = []
        params = {'id': product_id}
        
        fields = ['title', 'slug', 'sku', 'price', 'original_price', 'discount_percent',
                  'short_description', 'description', 'color', 'color_hex', 'is_best_seller',
                  'is_featured', 'is_new', 'in_stock']
        
        for field in fields:
            if field in data:
                updates.append(f'{field} = :{field}')
                params[field] = data[field]
        
        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            query = f"UPDATE products SET {', '.join(updates)} WHERE id = :id"
            db.session.execute(text(query), params)
            db.session.commit()
        
        return jsonify({'message': 'Product updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update product error: {str(e)}')
        return jsonify({'error': 'Failed to update product'}), 500


@admin_bp.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product (soft delete)"""
    try:
        db.session.execute(
            text('UPDATE products SET is_active = false WHERE id = :id'),
            {'id': product_id}
        )
        db.session.commit()
        
        return jsonify({'message': 'Product deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete product error: {str(e)}')
        return jsonify({'error': 'Failed to delete product'}), 500


# ============================================================
# Orders Management
# ============================================================

@admin_bp.route('/orders', methods=['GET'])
def get_all_orders():
    """Get all orders"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        status = request.args.get('status', type=str)
        
        offset = (page - 1) * limit
        
        query = 'SELECT * FROM orders WHERE 1=1'
        params = {}
        
        if status:
            query += ' AND status = :status'
            params['status'] = status
        
        query += ' ORDER BY created_at DESC LIMIT :limit OFFSET :offset'
        params['limit'] = limit
        params['offset'] = offset
        
        orders = db.session.execute(text(query), params).fetchall()
        
        # Get total count
        count_query = 'SELECT COUNT(*) FROM orders WHERE 1=1'
        count_params = {}
        if status:
            count_query += ' AND status = :status'
            count_params['status'] = status
        
        total = db.session.execute(text(count_query), count_params).scalar()
        
        orders_list = [
            {
                'id': str(o[0]),
                'order_number': o[1],
                'customer_email': o[4],
                'total': float(o[11]),
                'status': o[12],
                'payment_status': o[14],
                'created_at': str(o[15])
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
        logger.error(f'Get all orders error: {str(e)}')
        return jsonify({'error': 'Failed to fetch orders'}), 500


@admin_bp.route('/orders/<order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    try:
        data = request.get_json()
        
        status = data.get('status')
        if not status:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
        if status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Valid options: {valid_statuses}'}), 400
        
        db.session.execute(
            text('UPDATE orders SET status = :status, updated_at = CURRENT_TIMESTAMP WHERE id = :id'),
            {'status': status, 'id': order_id}
        )
        db.session.commit()
        
        return jsonify({'message': 'Order status updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update order status error: {str(e)}')
        return jsonify({'error': 'Failed to update order status'}), 500


# ============================================================
# Users Management
# ============================================================

@admin_bp.route('/users', methods=['GET'])
def get_all_users():
    """Get all users"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        offset = (page - 1) * limit
        
        users = db.session.execute(
            text('''
                SELECT id, email, first_name, last_name, is_active, is_admin, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            '''),
            {'limit': limit, 'offset': offset}
        ).fetchall()
        
        total = db.session.execute(text('SELECT COUNT(*) FROM users')).scalar()
        
        users_list = [
            {
                'id': str(u[0]),
                'email': u[1],
                'first_name': u[2],
                'last_name': u[3],
                'is_active': u[4],
                'is_admin': u[5],
                'created_at': str(u[6])
            } for u in users
        ]
        
        return jsonify({
            'users': users_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Get all users error: {str(e)}')
        return jsonify({'error': 'Failed to fetch users'}), 500


@admin_bp.route('/users/<user_id>/status', methods=['PUT'])
def toggle_user_status(user_id):
    """Activate/Deactivate user"""
    try:
        data = request.get_json()
        
        is_active = data.get('is_active')
        if is_active is None:
            return jsonify({'error': 'is_active is required'}), 400
        
        db.session.execute(
            text('UPDATE users SET is_active = :is_active WHERE id = :id'),
            {'is_active': is_active, 'id': user_id}
        )
        db.session.commit()
        
        return jsonify({'message': 'User status updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Toggle user status error: {str(e)}')
        return jsonify({'error': 'Failed to update user status'}), 500


# ============================================================
# Coupons Management
# ============================================================

@admin_bp.route('/coupons', methods=['POST'])
def create_coupon():
    """Create new coupon"""
    try:
        data = request.get_json()
        
        required = ['code', 'discount_type', 'discount_value']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        coupon_id = uuid.uuid4()
        
        db.session.execute(
            text('''
                INSERT INTO coupons (
                    id, code, discount_type, discount_value, description,
                    minimum_purchase, max_uses, valid_from, valid_until, is_active, created_at
                ) VALUES (
                    :id, :code, :discount_type, :discount_value, :description,
                    :minimum_purchase, :max_uses, :valid_from, :valid_until, true, CURRENT_TIMESTAMP
                )
            '''),
            {
                'id': str(coupon_id),
                'code': data['code'].upper().strip(),
                'discount_type': data['discount_type'],
                'discount_value': data['discount_value'],
                'description': data.get('description', ''),
                'minimum_purchase': data.get('minimum_purchase'),
                'max_uses': data.get('max_uses'),
                'valid_from': data.get('valid_from'),
                'valid_until': data.get('valid_until')
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Coupon created successfully',
            'coupon_id': str(coupon_id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create coupon error: {str(e)}')
        return jsonify({'error': 'Failed to create coupon'}), 500


# ============================================================
# Analytics
# ============================================================

@admin_bp.route('/analytics/sales', methods=['GET'])
def get_sales_analytics():
    """Get sales analytics"""
    try:
        period = request.args.get('period', 'monthly', type=str)
        
        # Basic sales data
        sales = db.session.execute(
            text('''
                SELECT DATE_TRUNC('day', created_at) as date, COUNT(*) as orders, SUM(total) as revenue
                FROM orders
                WHERE status = 'Completed'
                GROUP BY DATE_TRUNC('day', created_at)
                ORDER BY date DESC
                LIMIT 30
            ''')
        ).fetchall()
        
        sales_data = [
            {
                'date': str(s[0]),
                'orders': s[1],
                'revenue': float(s[2]) if s[2] else 0
            } for s in sales
        ]
        
        return jsonify({'sales': sales_data}), 200
        
    except Exception as e:
        logger.error(f'Get sales analytics error: {str(e)}')
        return jsonify({'error': 'Failed to fetch analytics'}), 500
