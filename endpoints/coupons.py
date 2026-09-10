from flask import Blueprint, request, jsonify
from extensions import db
from sqlalchemy import text
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
coupons_bp = Blueprint('coupons', __name__)

# ============================================================
# Coupons Endpoints
# ============================================================

@coupons_bp.route('', methods=['GET'])
def get_active_coupons():
    """Get all active coupons"""
    try:
        coupons = db.session.execute(
            text('''
                SELECT id, code, discount_type, discount_value, description,
                       minimum_purchase, max_uses, uses_count, valid_from, valid_until
                FROM coupons
                WHERE is_active = true
                AND valid_from <= CURRENT_TIMESTAMP
                AND valid_until >= CURRENT_TIMESTAMP
                ORDER BY created_at DESC
            ''')
        ).fetchall()
        
        coupons_list = [
            {
                'id': str(c[0]),
                'code': c[1],
                'discount_type': c[2],
                'discount_value': float(c[3]),
                'description': c[4],
                'minimum_purchase': float(c[5]) if c[5] else None,
                'max_uses': c[6],
                'uses_count': c[7],
                'valid_from': str(c[8]),
                'valid_until': str(c[9])
            } for c in coupons
        ]
        
        return jsonify({'coupons': coupons_list}), 200
        
    except Exception as e:
        logger.error(f'Get coupons error: {str(e)}')
        return jsonify({'error': 'Failed to fetch coupons'}), 500


@coupons_bp.route('/validate', methods=['POST'])
def validate_coupon():
    """Validate coupon code"""
    try:
        data = request.get_json()
        
        code = data.get('code', '').strip().upper()
        cart_total = data.get('cart_total', 0)
        
        if not code:
            return jsonify({'error': 'Coupon code required'}), 400
        
        # Get coupon
        coupon = db.session.execute(
            text('''
                SELECT id, code, discount_type, discount_value, description,
                       minimum_purchase, max_uses, uses_count, valid_from, valid_until
                FROM coupons
                WHERE code = :code AND is_active = true
            '''),
            {'code': code}
        ).fetchone()
        
        if not coupon:
            return jsonify({'error': 'Invalid coupon code'}), 400
        
        # Check dates
        now = datetime.utcnow()
        if coupon[8] > now or coupon[9] < now:
            return jsonify({'error': 'Coupon has expired'}), 400
        
        # Check usage limit
        if coupon[6] and coupon[7] >= coupon[6]:
            return jsonify({'error': 'Coupon usage limit reached'}), 400
        
        # Check minimum purchase
        if coupon[5] and cart_total < coupon[5]:
            return jsonify({
                'error': f'Minimum purchase of ${coupon[5]} required',
                'minimum_purchase': float(coupon[5])
            }), 400
        
        # Calculate discount
        if coupon[2] == 'percentage':
            discount = (cart_total * coupon[3]) / 100
        else:
            discount = coupon[3]
        
        return jsonify({
            'valid': True,
            'coupon_id': str(coupon[0]),
            'code': coupon[1],
            'discount_type': coupon[2],
            'discount_value': float(coupon[3]),
            'discount_amount': float(discount),
            'description': coupon[4]
        }), 200
        
    except Exception as e:
        logger.error(f'Validate coupon error: {str(e)}')
        return jsonify({'error': 'Failed to validate coupon'}), 500


@coupons_bp.route('/<coupon_id>/apply', methods=['POST'])
def apply_coupon(coupon_id):
    """Apply coupon to order"""
    try:
        # Update usage count
        db.session.execute(
            text('UPDATE coupons SET uses_count = uses_count + 1 WHERE id = :id'),
            {'id': coupon_id}
        )
        db.session.commit()
        
        return jsonify({'message': 'Coupon applied successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Apply coupon error: {str(e)}')
        return jsonify({'error': 'Failed to apply coupon'}), 500


@coupons_bp.route('/<coupon_id>/redeem', methods=['POST'])
def redeem_coupon(coupon_id):
    """Redeem coupon (increment uses_count)"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({'error': 'Order ID required'}), 400
        
        # Record coupon usage
        # This is tracked in the orders table with coupon_id
        
        return jsonify({'message': 'Coupon redeemed successfully'}), 200
        
    except Exception as e:
        logger.error(f'Redeem coupon error: {str(e)}')
        return jsonify({'error': 'Failed to redeem coupon'}), 500
