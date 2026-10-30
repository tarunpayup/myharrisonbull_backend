from flask import Blueprint, jsonify
import logging

from services import evaluate_coupon, serialize_coupon
from utils import error, json_body, query_all

logger = logging.getLogger(__name__)
coupons_bp = Blueprint('coupons', __name__)

# ============================================================
# Coupons Endpoints
# ============================================================
# Usage is counted when an order is placed (see orders.create_order), so there
# are deliberately no public "apply"/"redeem" endpoints that could be abused.

@coupons_bp.route('', methods=['GET'])
def get_active_coupons():
    """Get coupons customers can currently use"""
    try:
        coupons = query_all(
            '''SELECT * FROM coupons
               WHERE is_active = true
                 AND (expires_at IS NULL OR expires_at >= CURRENT_TIMESTAMP)
                 AND (max_uses IS NULL OR used_count < max_uses)
               ORDER BY created_at DESC''')
        return jsonify({'coupons': [serialize_coupon(c) for c in coupons]}), 200

    except Exception as e:
        logger.error(f'Get coupons error: {str(e)}')
        return error('Failed to fetch coupons', 500)


@coupons_bp.route('/validate', methods=['POST'])
def validate_coupon():
    """Validate a coupon code against the cart subtotal"""
    try:
        data = json_body()
        try:
            cart_total = float(data.get('cart_total', 0))
        except (TypeError, ValueError):
            return error('cart_total must be a number')

        coupon, discount, problem = evaluate_coupon(data.get('code'), cart_total)
        if problem:
            return error(problem)

        info = serialize_coupon(coupon)
        return jsonify({
            'valid': True,
            'coupon_id': info['id'],
            'code': info['code'],
            'discount_type': info['discount_type'],
            'discount_value': info['discount_value'],
            'discount_percent': info['discount_percent'],
            'discount_amount': float(discount),
            'min_spend': info['min_spend'],
            'description': info['description'],
            'message': f'Coupon {info["code"]} applied successfully!',
        }), 200

    except Exception as e:
        logger.error(f'Validate coupon error: {str(e)}')
        return error('Failed to validate coupon', 500)
