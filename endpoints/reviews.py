from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from sqlalchemy import text
import logging
import uuid

logger = logging.getLogger(__name__)
reviews_bp = Blueprint('reviews', __name__)

# ============================================================
# Product Reviews Endpoints
# ============================================================

@reviews_bp.route('', methods=['GET'])
def get_reviews():
    """Get reviews for a product"""
    try:
        product_id = request.args.get('product_id')
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        
        if not product_id:
            return jsonify({'error': 'Product ID required'}), 400
        
        offset = (page - 1) * limit
        
        reviews = db.session.execute(
            text('''
                SELECT id, user_id, product_id, rating, title, comment,
                       is_verified_purchase, helpful_count, unhelpful_count, created_at
                FROM product_reviews
                WHERE product_id = :product_id AND is_active = true
                ORDER BY helpful_count DESC, created_at DESC
                LIMIT :limit OFFSET :offset
            '''),
            {'product_id': product_id, 'limit': limit, 'offset': offset}
        ).fetchall()
        
        # Get total count
        total = db.session.execute(
            text('''
                SELECT COUNT(*) FROM product_reviews
                WHERE product_id = :product_id AND is_active = true
            '''),
            {'product_id': product_id}
        ).scalar()
        
        reviews_list = [
            {
                'id': str(r[0]),
                'user_id': str(r[1]) if r[1] else None,
                'rating': r[3],
                'title': r[4],
                'comment': r[5],
                'is_verified_purchase': r[6],
                'helpful_count': r[7],
                'unhelpful_count': r[8],
                'created_at': str(r[9])
            } for r in reviews
        ]
        
        return jsonify({
            'reviews': reviews_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Get reviews error: {str(e)}')
        return jsonify({'error': 'Failed to fetch reviews'}), 500


@reviews_bp.route('', methods=['POST'])
@jwt_required()
def create_review():
    """Create product review"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        product_id = data.get('product_id')
        rating = data.get('rating', 5)
        title = data.get('title', '').strip()
        comment = data.get('comment', '').strip()
        
        if not product_id:
            return jsonify({'error': 'Product ID required'}), 400
        
        if not (1 <= rating <= 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        if not title or len(title) < 3:
            return jsonify({'error': 'Title must be at least 3 characters'}), 400
        
        if not comment or len(comment) < 10:
            return jsonify({'error': 'Comment must be at least 10 characters'}), 400
        
        # Check if product exists
        product = db.session.execute(
            text('SELECT id FROM products WHERE id = :id'),
            {'id': product_id}
        ).fetchone()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Check if user has already reviewed this product
        existing_review = db.session.execute(
            text('''
                SELECT id FROM product_reviews
                WHERE user_id = :user_id AND product_id = :product_id
            '''),
            {'user_id': user_id, 'product_id': product_id}
        ).fetchone()
        
        if existing_review:
            return jsonify({'error': 'You have already reviewed this product'}), 400
        
        # Check if user purchased this product
        verified_purchase = db.session.execute(
            text('''
                SELECT COUNT(*) FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                WHERE o.user_id = :user_id AND oi.product_id = :product_id
            '''),
            {'user_id': user_id, 'product_id': product_id}
        ).scalar() > 0
        
        review_id = uuid.uuid4()
        
        db.session.execute(
            text('''
                INSERT INTO product_reviews (
                    id, user_id, product_id, rating, title, comment,
                    is_verified_purchase, helpful_count, unhelpful_count, is_active, created_at
                ) VALUES (
                    :id, :user_id, :product_id, :rating, :title, :comment,
                    :verified_purchase, 0, 0, true, CURRENT_TIMESTAMP
                )
            '''),
            {
                'id': str(review_id),
                'user_id': user_id,
                'product_id': product_id,
                'rating': rating,
                'title': title,
                'comment': comment,
                'verified_purchase': verified_purchase
            }
        )
        
        # Update product rating
        stats = db.session.execute(
            text('''
                SELECT AVG(rating), COUNT(*) FROM product_reviews
                WHERE product_id = :product_id AND is_active = true
            '''),
            {'product_id': product_id}
        ).fetchone()
        
        db.session.execute(
            text('''
                UPDATE products SET rating = :rating, reviews_count = :count
                WHERE id = :id
            '''),
            {
                'rating': float(stats[0]) if stats[0] else 0,
                'count': int(stats[1]),
                'id': product_id
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Review created successfully',
            'review_id': str(review_id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create review error: {str(e)}')
        return jsonify({'error': 'Failed to create review'}), 500


@reviews_bp.route('/<review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    """Delete review (soft delete)"""
    try:
        user_id = get_jwt_identity()
        
        review = db.session.execute(
            text('SELECT product_id FROM product_reviews WHERE id = :id AND user_id = :user_id'),
            {'id': review_id, 'user_id': user_id}
        ).fetchone()
        
        if not review:
            return jsonify({'error': 'Review not found'}), 404
        
        product_id = review[0]
        
        # Soft delete
        db.session.execute(
            text('UPDATE product_reviews SET is_active = false WHERE id = :id'),
            {'id': review_id}
        )
        
        # Update product rating
        stats = db.session.execute(
            text('''
                SELECT AVG(rating), COUNT(*) FROM product_reviews
                WHERE product_id = :product_id AND is_active = true
            '''),
            {'product_id': product_id}
        ).fetchone()
        
        db.session.execute(
            text('''
                UPDATE products SET rating = :rating, reviews_count = :count
                WHERE id = :id
            '''),
            {
                'rating': float(stats[0]) if stats[0] else 0,
                'count': int(stats[1]),
                'id': product_id
            }
        )
        
        db.session.commit()
        
        return jsonify({'message': 'Review deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete review error: {str(e)}')
        return jsonify({'error': 'Failed to delete review'}), 500


@reviews_bp.route('/<review_id>/helpful', methods=['POST'])
def mark_helpful(review_id):
    """Mark review as helpful"""
    try:
        db.session.execute(
            text('UPDATE product_reviews SET helpful_count = helpful_count + 1 WHERE id = :id'),
            {'id': review_id}
        )
        db.session.commit()
        
        return jsonify({'message': 'Marked as helpful'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Mark helpful error: {str(e)}')
        return jsonify({'error': 'Failed to mark as helpful'}), 500


@reviews_bp.route('/<review_id>/unhelpful', methods=['POST'])
def mark_unhelpful(review_id):
    """Mark review as unhelpful"""
    try:
        db.session.execute(
            text('UPDATE product_reviews SET unhelpful_count = unhelpful_count + 1 WHERE id = :id'),
            {'id': review_id}
        )
        db.session.commit()
        
        return jsonify({'message': 'Marked as unhelpful'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Mark unhelpful error: {str(e)}')
        return jsonify({'error': 'Failed to mark as unhelpful'}), 500
