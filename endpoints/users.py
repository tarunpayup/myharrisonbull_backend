from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from sqlalchemy import text
import logging
import uuid

logger = logging.getLogger(__name__)
users_bp = Blueprint('users', __name__)

# ============================================================
# Users Endpoints (Profile, Addresses, Wishlist)
# ============================================================

@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile"""
    try:
        user_id = get_jwt_identity()
        
        user = db.session.execute(
            text('''
                SELECT id, email, first_name, last_name, phone, avatar_url,
                       newsletter_subscribed, promotions_enabled, created_at
                FROM users WHERE id = :id
            '''),
            {'id': user_id}
        ).fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': {
                'id': str(user[0]),
                'email': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'phone': user[4],
                'avatar_url': user[5],
                'newsletter_subscribed': user[6],
                'promotions_enabled': user[7],
                'created_at': str(user[8])
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Get profile error: {str(e)}')
        return jsonify({'error': 'Failed to fetch profile'}), 500


@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update fields
        updates = []
        params = {'id': user_id}
        
        if 'first_name' in data:
            updates.append('first_name = :first_name')
            params['first_name'] = data['first_name'].strip()
        
        if 'last_name' in data:
            updates.append('last_name = :last_name')
            params['last_name'] = data['last_name'].strip()
        
        if 'phone' in data:
            updates.append('phone = :phone')
            params['phone'] = data['phone'].strip()
        
        if 'avatar_url' in data:
            updates.append('avatar_url = :avatar_url')
            params['avatar_url'] = data['avatar_url']
        
        if 'newsletter_subscribed' in data:
            updates.append('newsletter_subscribed = :newsletter_subscribed')
            params['newsletter_subscribed'] = data['newsletter_subscribed']
        
        if 'promotions_enabled' in data:
            updates.append('promotions_enabled = :promotions_enabled')
            params['promotions_enabled'] = data['promotions_enabled']
        
        if not updates:
            return jsonify({'error': 'No fields to update'}), 400
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = :id"
        db.session.execute(text(query), params)
        db.session.commit()
        
        return jsonify({'message': 'Profile updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update profile error: {str(e)}')
        return jsonify({'error': 'Failed to update profile'}), 500


@users_bp.route('/addresses', methods=['GET'])
@jwt_required()
def get_addresses():
    """Get user addresses"""
    try:
        user_id = get_jwt_identity()
        
        addresses = db.session.execute(
            text('''
                SELECT id, first_name, last_name, company_name, street_address,
                       city, state, postal_code, country, phone, is_default, address_type
                FROM addresses WHERE user_id = :user_id
                ORDER BY is_default DESC, created_at DESC
            '''),
            {'user_id': user_id}
        ).fetchall()
        
        addresses_list = [
            {
                'id': str(a[0]),
                'first_name': a[1],
                'last_name': a[2],
                'company_name': a[3],
                'street_address': a[4],
                'city': a[5],
                'state': a[6],
                'postal_code': a[7],
                'country': a[8],
                'phone': a[9],
                'is_default': a[10],
                'address_type': a[11]
            } for a in addresses
        ]
        
        return jsonify({'addresses': addresses_list}), 200
        
    except Exception as e:
        logger.error(f'Get addresses error: {str(e)}')
        return jsonify({'error': 'Failed to fetch addresses'}), 500


@users_bp.route('/addresses', methods=['POST'])
@jwt_required()
def create_address():
    """Create new address"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required = ['first_name', 'last_name', 'street_address', 'city', 'state', 'postal_code', 'country', 'phone']
        if not all(data.get(field) for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        address_id = uuid.uuid4()
        
        db.session.execute(
            text('''
                INSERT INTO addresses (
                    id, user_id, first_name, last_name, company_name,
                    street_address, city, state, postal_code, country,
                    phone, is_default, address_type, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :first_name, :last_name, :company_name,
                    :street_address, :city, :state, :postal_code, :country,
                    :phone, :is_default, :address_type, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            '''),
            {
                'id': str(address_id),
                'user_id': user_id,
                'first_name': data['first_name'].strip(),
                'last_name': data['last_name'].strip(),
                'company_name': data.get('company_name', '').strip(),
                'street_address': data['street_address'].strip(),
                'city': data['city'].strip(),
                'state': data['state'].strip(),
                'postal_code': data['postal_code'].strip(),
                'country': data['country'].strip(),
                'phone': data['phone'].strip(),
                'is_default': data.get('is_default', False),
                'address_type': data.get('address_type', 'billing')
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Address created successfully',
            'address_id': str(address_id)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Create address error: {str(e)}')
        return jsonify({'error': 'Failed to create address'}), 500


@users_bp.route('/addresses/<address_id>', methods=['PUT'])
@jwt_required()
def update_address(address_id):
    """Update address"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Verify address belongs to user
        address = db.session.execute(
            text('SELECT id FROM addresses WHERE id = :id AND user_id = :user_id'),
            {'id': address_id, 'user_id': user_id}
        ).fetchone()
        
        if not address:
            return jsonify({'error': 'Address not found'}), 404
        
        # Update
        updates = []
        params = {'id': address_id, 'user_id': user_id}
        
        for field in ['first_name', 'last_name', 'street_address', 'city', 'state', 'postal_code', 'country', 'phone']:
            if field in data:
                updates.append(f'{field} = :{field}')
                params[field] = data[field].strip()
        
        if 'is_default' in data:
            updates.append('is_default = :is_default')
            params['is_default'] = data['is_default']
        
        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            query = f"UPDATE addresses SET {', '.join(updates)} WHERE id = :id AND user_id = :user_id"
            db.session.execute(text(query), params)
            db.session.commit()
        
        return jsonify({'message': 'Address updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Update address error: {str(e)}')
        return jsonify({'error': 'Failed to update address'}), 500


@users_bp.route('/addresses/<address_id>', methods=['DELETE'])
@jwt_required()
def delete_address(address_id):
    """Delete address"""
    try:
        user_id = get_jwt_identity()
        
        result = db.session.execute(
            text('DELETE FROM addresses WHERE id = :id AND user_id = :user_id'),
            {'id': address_id, 'user_id': user_id}
        )
        
        if result.rowcount == 0:
            return jsonify({'error': 'Address not found'}), 404
        
        db.session.commit()
        
        return jsonify({'message': 'Address deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete address error: {str(e)}')
        return jsonify({'error': 'Failed to delete address'}), 500


@users_bp.route('/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    """Get user wishlist"""
    try:
        user_id = get_jwt_identity()
        
        wishlist = db.session.execute(
            text('''
                SELECT w.id, w.product_id, p.title, p.price, p.rating
                FROM wishlist_items w
                JOIN products p ON w.product_id = p.id
                WHERE w.user_id = :user_id
                ORDER BY w.added_at DESC
            '''),
            {'user_id': user_id}
        ).fetchall()
        
        items = [
            {
                'id': str(w[0]),
                'product_id': str(w[1]),
                'title': w[2],
                'price': float(w[3]),
                'rating': float(w[4])
            } for w in wishlist
        ]
        
        return jsonify({'wishlist': items}), 200
        
    except Exception as e:
        logger.error(f'Get wishlist error: {str(e)}')
        return jsonify({'error': 'Failed to fetch wishlist'}), 500


@users_bp.route('/wishlist', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    """Add product to wishlist"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        product_id = data.get('product_id')
        if not product_id:
            return jsonify({'error': 'Product ID required'}), 400
        
        # Check if product exists
        product = db.session.execute(
            text('SELECT id FROM products WHERE id = :id'),
            {'id': product_id}
        ).fetchone()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        item_id = uuid.uuid4()
        
        try:
            db.session.execute(
                text('''
                    INSERT INTO wishlist_items (id, user_id, product_id, added_at)
                    VALUES (:id, :user_id, :product_id, CURRENT_TIMESTAMP)
                '''),
                {'id': str(item_id), 'user_id': user_id, 'product_id': product_id}
            )
            db.session.commit()
            
            return jsonify({'message': 'Added to wishlist', 'item_id': str(item_id)}), 201
        except:
            db.session.rollback()
            return jsonify({'error': 'Already in wishlist'}), 400
        
    except Exception as e:
        logger.error(f'Add to wishlist error: {str(e)}')
        return jsonify({'error': 'Failed to add to wishlist'}), 500


@users_bp.route('/wishlist/<product_id>', methods=['DELETE'])
@jwt_required()
def remove_from_wishlist(product_id):
    """Remove product from wishlist"""
    try:
        user_id = get_jwt_identity()
        
        result = db.session.execute(
            text('''
                DELETE FROM wishlist_items
                WHERE user_id = :user_id AND product_id = :product_id
            '''),
            {'user_id': user_id, 'product_id': product_id}
        )
        
        if result.rowcount == 0:
            return jsonify({'error': 'Item not in wishlist'}), 404
        
        db.session.commit()
        
        return jsonify({'message': 'Removed from wishlist'}), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Remove from wishlist error: {str(e)}')
        return jsonify({'error': 'Failed to remove from wishlist'}), 500
