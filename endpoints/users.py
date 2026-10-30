from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
import logging

from extensions import db
from services import PRODUCT_SELECT, serialize_address, serialize_products, serialize_user, user_stats
from utils import clean_str, error, execute, is_uuid, json_body, query_all, query_one, split_name

logger = logging.getLogger(__name__)
users_bp = Blueprint('users', __name__)

# ============================================================
# Users Endpoints (Profile, Addresses, Wishlist)
# ============================================================

PROFILE_FIELDS = ('first_name', 'last_name', 'phone', 'avatar_url', 'newsletter_subscribed',
                  'promotions_enabled', 'preferred_shoe_size', 'preferred_width')


def _load_profile(user_id):
    user = query_one('SELECT * FROM users WHERE id = :id', id=user_id)
    if not user:
        return None
    return serialize_user(user, user_stats([user['id']]).get(user['id'], {}))


@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get user profile (with their saved addresses, as the frontend profile object expects)"""
    try:
        user_id = get_jwt_identity()
        profile = _load_profile(user_id)
        if not profile:
            return error('User not found', 404)
        addresses = query_all(
            'SELECT * FROM addresses WHERE user_id = :id ORDER BY is_default DESC, created_at DESC', id=user_id)
        profile['addresses'] = [serialize_address(a) for a in addresses]
        return jsonify({'user': profile}), 200

    except Exception as e:
        logger.error(f'Get profile error: {str(e)}')
        return error('Failed to fetch profile', 500)


@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        user_id = get_jwt_identity()
        data = json_body()
        if not data:
            return error('No data provided')

        values = {}
        if 'name' in data:  # the frontend edits a single "name" field
            values['first_name'], values['last_name'] = split_name(data['name'])
            if not values['first_name']:
                return error('Name cannot be empty')
        for field in PROFILE_FIELDS:
            if field in data:
                values[field] = clean_str(data[field]) if isinstance(data[field], str) else data[field]

        if not values:
            return error('No fields to update')
        if 'first_name' in values and not values['first_name']:
            return error('First name cannot be empty')

        assignments = ', '.join(f'{field} = :{field}' for field in values)
        execute(f'UPDATE users SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = :id', id=user_id, **values)
        db.session.commit()

        return jsonify({'message': 'Profile updated successfully', 'user': _load_profile(user_id)}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Update profile error: {str(e)}')
        return error('Failed to update profile', 500)


# ------------------------------------------------------------
# Addresses
# ------------------------------------------------------------

def _address_values(data):
    """Map frontend/camelCase-ish address input onto address columns."""
    values = {}
    if 'full_name' in data or 'fullName' in data:
        values['first_name'], values['last_name'] = split_name(data.get('full_name') or data.get('fullName'))
    for field in ('first_name', 'last_name'):
        if field in data:
            values[field] = clean_str(data[field])
    aliases = {
        'street_address': ('street_address', 'street'),
        'apartment': ('apartment',),
        'company_name': ('company_name',),
        'city': ('city',),
        'state': ('state',),
        'postal_code': ('postal_code', 'postalCode'),
        'country': ('country',),
        'phone': ('phone',),
        'address_type': ('address_type', 'addressType'),
    }
    for column, names in aliases.items():
        for name in names:
            if name in data:
                values[column] = clean_str(data[name])
                break
    for name in ('is_default', 'isDefault', 'is_default_shipping', 'isDefaultShipping'):
        if name in data:
            values['is_default'] = bool(data[name])
            break
    return values


def _clear_other_defaults(user_id, keep_id):
    execute('UPDATE addresses SET is_default = false WHERE user_id = :user_id AND id <> :id',
            user_id=user_id, id=keep_id)


@users_bp.route('/addresses', methods=['GET'])
@jwt_required()
def get_addresses():
    """Get user addresses"""
    try:
        rows = query_all(
            'SELECT * FROM addresses WHERE user_id = :user_id ORDER BY is_default DESC, created_at DESC',
            user_id=get_jwt_identity())
        return jsonify({'addresses': [serialize_address(a) for a in rows]}), 200

    except Exception as e:
        logger.error(f'Get addresses error: {str(e)}')
        return error('Failed to fetch addresses', 500)


@users_bp.route('/addresses', methods=['POST'])
@jwt_required()
def create_address():
    """Create new address"""
    try:
        user_id = get_jwt_identity()
        values = _address_values(json_body())

        required = ['first_name', 'street_address', 'city', 'postal_code', 'country', 'phone']
        if not all(values.get(field) for field in required):
            return error('Missing required fields: full name, phone, street, city, postal code, country')
        values.setdefault('last_name', '')
        values.setdefault('state', '')
        values.setdefault('address_type', 'Home')

        # The first address a customer saves becomes their default
        has_addresses = query_one('SELECT 1 AS found FROM addresses WHERE user_id = :id LIMIT 1', id=user_id)
        values.setdefault('is_default', not has_addresses)

        columns = ', '.join(values)
        placeholders = ', '.join(f':{c}' for c in values)
        address = query_one(
            f'INSERT INTO addresses (user_id, {columns}) VALUES (:user_id, {placeholders}) RETURNING *',
            user_id=user_id, **values)
        if address['is_default']:
            _clear_other_defaults(user_id, address['id'])
        db.session.commit()

        return jsonify({
            'message': 'Address created successfully',
            'address_id': str(address['id']),
            'address': serialize_address(address),
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'Create address error: {str(e)}')
        return error('Failed to create address', 500)


@users_bp.route('/addresses/<address_id>', methods=['PUT'])
@jwt_required()
def update_address(address_id):
    """Update address (send is_default: true to make it the default)"""
    try:
        user_id = get_jwt_identity()
        if not is_uuid(address_id):
            return error('Address not found', 404)
        values = _address_values(json_body())

        if values:
            assignments = ', '.join(f'{c} = :{c}' for c in values)
            address = query_one(
                f'''UPDATE addresses SET {assignments}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id AND user_id = :user_id RETURNING *''',
                id=address_id, user_id=user_id, **values)
        else:
            address = query_one('SELECT * FROM addresses WHERE id = :id AND user_id = :user_id',
                                id=address_id, user_id=user_id)
        if not address:
            return error('Address not found', 404)

        if values.get('is_default'):
            _clear_other_defaults(user_id, address['id'])
        db.session.commit()

        return jsonify({'message': 'Address updated successfully', 'address': serialize_address(address)}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Update address error: {str(e)}')
        return error('Failed to update address', 500)


@users_bp.route('/addresses/<address_id>', methods=['DELETE'])
@jwt_required()
def delete_address(address_id):
    """Delete address"""
    try:
        user_id = get_jwt_identity()
        if not is_uuid(address_id):
            return error('Address not found', 404)

        # Orders keep a JSON snapshot of the address, so detaching the FK loses nothing
        execute('UPDATE orders SET shipping_address_id = NULL WHERE shipping_address_id = :id', id=address_id)
        result = execute('DELETE FROM addresses WHERE id = :id AND user_id = :user_id', id=address_id, user_id=user_id)
        if result.rowcount == 0:
            db.session.rollback()
            return error('Address not found', 404)
        db.session.commit()

        return jsonify({'message': 'Address deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Delete address error: {str(e)}')
        return error('Failed to delete address', 500)


# ------------------------------------------------------------
# Wishlist
# ------------------------------------------------------------

@users_bp.route('/wishlist', methods=['GET'])
@jwt_required()
def get_wishlist():
    """Get user wishlist as full product objects"""
    try:
        rows = query_all(
            f'''{PRODUCT_SELECT}
                JOIN wishlist_items w ON w.product_id = p.id
                WHERE w.user_id = :user_id AND p.is_active = true
                ORDER BY w.added_at DESC''',
            user_id=get_jwt_identity())
        products = serialize_products(rows)
        return jsonify({
            'wishlist': products,
            'product_ids': [p['id'] for p in products],
        }), 200

    except Exception as e:
        logger.error(f'Get wishlist error: {str(e)}')
        return error('Failed to fetch wishlist', 500)


@users_bp.route('/wishlist', methods=['POST'])
@jwt_required()
def add_to_wishlist():
    """Add product to wishlist (adding twice is a no-op)"""
    try:
        user_id = get_jwt_identity()
        product_id = json_body().get('product_id')
        if not product_id:
            return error('Product ID required')
        if not is_uuid(product_id) or not query_one(
            'SELECT id FROM products WHERE id = :id AND is_active = true', id=product_id
        ):
            return error('Product not found', 404)

        inserted = execute(
            '''INSERT INTO wishlist_items (user_id, product_id) VALUES (:user_id, :product_id)
               ON CONFLICT (user_id, product_id) DO NOTHING''', user_id=user_id, product_id=product_id)
        db.session.commit()

        return jsonify({'message': 'Added to wishlist' if inserted.rowcount else 'Already in wishlist'}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'Add to wishlist error: {str(e)}')
        return error('Failed to add to wishlist', 500)


@users_bp.route('/wishlist/<product_id>', methods=['DELETE'])
@jwt_required()
def remove_from_wishlist(product_id):
    """Remove product from wishlist"""
    try:
        if not is_uuid(product_id):
            return error('Item not in wishlist', 404)
        result = execute('DELETE FROM wishlist_items WHERE user_id = :user_id AND product_id = :product_id',
                         user_id=get_jwt_identity(), product_id=product_id)
        if result.rowcount == 0:
            return error('Item not in wishlist', 404)
        db.session.commit()

        return jsonify({'message': 'Removed from wishlist'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Remove from wishlist error: {str(e)}')
        return error('Failed to remove from wishlist', 500)
