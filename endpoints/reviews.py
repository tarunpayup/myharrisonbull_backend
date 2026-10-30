from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
import logging

from extensions import db
from services import refresh_product_rating, serialize_review
from utils import clean_str, error, execute, is_uuid, json_body, pagination, paging, query_all, query_one, query_scalar

logger = logging.getLogger(__name__)
reviews_bp = Blueprint('reviews', __name__)

FIT_OPTIONS = ('Runs Small', 'True to Size', 'Runs Large')

REVIEW_SELECT = '''
    SELECT r.*, p.title AS product_title FROM product_reviews r JOIN products p ON p.id = r.product_id
'''

# ============================================================
# Product Reviews Endpoints
# ============================================================
# New reviews start as "Pending" and only show publicly (and count towards the
# product rating) once an admin approves them - see admin.py.

@reviews_bp.route('', methods=['GET'])
def get_reviews():
    """Approved reviews for a product (or the latest approved reviews when no product is given)"""
    try:
        product_id = request.args.get('product_id')
        page, limit, offset = paging()

        where, params = ["r.status = 'Approved'"], {}
        if product_id:
            if not is_uuid(product_id):
                return jsonify({'reviews': [], 'pagination': pagination(page, limit, 0)}), 200
            where.append('r.product_id = :product_id')
            params['product_id'] = product_id
        clause = ' AND '.join(where)

        rows = query_all(
            f'''{REVIEW_SELECT} WHERE {clause}
                ORDER BY r.helpful_count DESC, r.created_at DESC LIMIT :limit OFFSET :offset''',
            limit=limit, offset=offset, **params)
        total = query_scalar(f'SELECT COUNT(*) FROM product_reviews r WHERE {clause}', **params)

        return jsonify({
            'reviews': [serialize_review(r) for r in rows],
            'pagination': pagination(page, limit, total),
        }), 200

    except Exception as e:
        logger.error(f'Get reviews error: {str(e)}')
        return error('Failed to fetch reviews', 500)


@reviews_bp.route('', methods=['POST'])
@jwt_required()
def create_review():
    """Submit a product review (held for moderation)"""
    try:
        user_id = get_jwt_identity()
        data = json_body()

        product_id = data.get('product_id') or data.get('shoe_id')
        rating = data.get('rating', 5)
        title = clean_str(data.get('title'))
        comment = clean_str(data.get('comment'))
        fit = data.get('fit_feedback') or 'True to Size'

        if not product_id or not is_uuid(product_id):
            return error('Product ID required')
        if not isinstance(rating, int) or isinstance(rating, bool) or not 1 <= rating <= 5:
            return error('Rating must be a whole number between 1 and 5')
        if len(title) < 3:
            return error('Title must be at least 3 characters')
        if len(comment) < 10:
            return error('Comment must be at least 10 characters')
        if fit not in FIT_OPTIONS:
            return error(f'fit_feedback must be one of {list(FIT_OPTIONS)}')

        if not query_one('SELECT id FROM products WHERE id = :id AND is_active = true', id=product_id):
            return error('Product not found', 404)
        if query_one('SELECT id FROM product_reviews WHERE user_id = :u AND product_id = :p', u=user_id, p=product_id):
            return error('You have already reviewed this product')

        user = query_one('SELECT first_name, last_name, email FROM users WHERE id = :id', id=user_id)
        verified = bool(query_scalar(
            '''SELECT COUNT(*) FROM order_items oi JOIN orders o ON o.id = oi.order_id
               WHERE o.user_id = :u AND oi.product_id = :p AND o.status <> 'Cancelled' ''', u=user_id, p=product_id))

        review = query_one(
            '''INSERT INTO product_reviews (product_id, user_id, customer_name, email, rating, title, comment,
                                            verified_purchase, is_approved, status, fit_feedback)
               VALUES (:product_id, :user_id, :name, :email, :rating, :title, :comment, :verified, false, 'Pending', :fit)
               RETURNING id''',
            product_id=product_id, user_id=user_id, name=f'{user["first_name"]} {user["last_name"]}'.strip(),
            email=user['email'], rating=rating, title=title, comment=comment, verified=verified, fit=fit)
        db.session.commit()

        return jsonify({
            'message': 'Thank you! Your review will appear once it has been approved.',
            'review_id': str(review['id']),
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'Create review error: {str(e)}')
        return error('Failed to create review', 500)


@reviews_bp.route('/<review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    """Delete your own review"""
    try:
        if not is_uuid(review_id):
            return error('Review not found', 404)
        review = query_one('SELECT product_id FROM product_reviews WHERE id = :id AND user_id = :u',
                           id=review_id, u=get_jwt_identity())
        if not review:
            return error('Review not found', 404)

        execute('DELETE FROM product_reviews WHERE id = :id', id=review_id)
        refresh_product_rating(review['product_id'])
        db.session.commit()

        return jsonify({'message': 'Review deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete review error: {str(e)}')
        return error('Failed to delete review', 500)


@reviews_bp.route('/<review_id>/helpful', methods=['POST'])
@jwt_required()
def mark_helpful(review_id):
    """Mark an approved review as helpful"""
    try:
        if not is_uuid(review_id):
            return error('Review not found', 404)
        result = execute(
            '''UPDATE product_reviews SET helpful_count = helpful_count + 1
               WHERE id = :id AND status = 'Approved' ''', id=review_id)
        if result.rowcount == 0:
            return error('Review not found', 404)
        db.session.commit()

        return jsonify({'message': 'Marked as helpful'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Mark helpful error: {str(e)}')
        return error('Failed to mark as helpful', 500)
