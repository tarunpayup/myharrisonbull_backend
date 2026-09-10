from flask import Blueprint, request, jsonify
from extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
stores_bp = Blueprint('stores', __name__)

# ============================================================
# Store Locations Endpoints
# ============================================================

@stores_bp.route('', methods=['GET'])
def get_stores():
    """Get all store locations"""
    try:
        stores = db.session.execute(
            text('''
                SELECT id, store_name, email, phone, street_address, city,
                       state, postal_code, country, latitude, longitude, is_active
                FROM store_locations
                WHERE is_active = true
                ORDER BY store_name
            ''')
        ).fetchall()
        
        stores_list = []
        for s in stores:
            stores_list.append({
                'id': str(s[0]),
                'store_name': s[1],
                'email': s[2],
                'phone': s[3],
                'address': {
                    'street': s[4],
                    'city': s[5],
                    'state': s[6],
                    'postal_code': s[7],
                    'country': s[8]
                },
                'coordinates': {
                    'latitude': s[9],
                    'longitude': s[10]
                }
            })
        
        return jsonify({'stores': stores_list}), 200
        
    except Exception as e:
        logger.error(f'Get stores error: {str(e)}')
        return jsonify({'error': 'Failed to fetch stores'}), 500


@stores_bp.route('/<store_id>', methods=['GET'])
def get_store(store_id):
    """Get store details with hours"""
    try:
        store = db.session.execute(
            text('''
                SELECT id, store_name, email, phone, street_address, city,
                       state, postal_code, country, latitude, longitude, description, is_active
                FROM store_locations
                WHERE id = :id AND is_active = true
            '''),
            {'id': store_id}
        ).fetchone()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        # Get store hours
        hours = db.session.execute(
            text('''
                SELECT day_of_week, opening_time, closing_time, is_closed
                FROM store_hours
                WHERE store_id = :store_id
                ORDER BY day_of_week
            '''),
            {'store_id': store_id}
        ).fetchall()
        
        hours_dict = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for h in hours:
            day = h[0]
            hours_dict[day] = {
                'opening_time': str(h[1]) if h[1] else None,
                'closing_time': str(h[2]) if h[2] else None,
                'is_closed': h[3]
            }
        
        # Fill missing days
        for day in days:
            if day not in hours_dict:
                hours_dict[day] = {
                    'opening_time': None,
                    'closing_time': None,
                    'is_closed': True
                }
        
        store_data = {
            'id': str(store[0]),
            'store_name': store[1],
            'email': store[2],
            'phone': store[3],
            'address': {
                'street': store[4],
                'city': store[5],
                'state': store[6],
                'postal_code': store[7],
                'country': store[8]
            },
            'coordinates': {
                'latitude': store[9],
                'longitude': store[10]
            },
            'description': store[11],
            'hours': hours_dict
        }
        
        return jsonify(store_data), 200
        
    except Exception as e:
        logger.error(f'Get store error: {str(e)}')
        return jsonify({'error': 'Failed to fetch store'}), 500


@stores_bp.route('/search', methods=['GET'])
def search_stores():
    """Search stores by city or state"""
    try:
        query = request.args.get('q', '', type=str)
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Search query too short'}), 400
        
        stores = db.session.execute(
            text('''
                SELECT id, store_name, city, state, phone
                FROM store_locations
                WHERE is_active = true AND (
                    city ILIKE :search OR
                    state ILIKE :search OR
                    store_name ILIKE :search
                )
                ORDER BY store_name
            '''),
            {'search': f'%{query}%'}
        ).fetchall()
        
        stores_list = [
            {
                'id': str(s[0]),
                'store_name': s[1],
                'city': s[2],
                'state': s[3],
                'phone': s[4]
            } for s in stores
        ]
        
        return jsonify({'results': stores_list}), 200
        
    except Exception as e:
        logger.error(f'Search stores error: {str(e)}')
        return jsonify({'error': 'Failed to search stores'}), 500


@stores_bp.route('/nearest', methods=['GET'])
def get_nearest_stores():
    """Get stores nearest to coordinates"""
    try:
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        limit = request.args.get('limit', 5, type=int)
        
        if not latitude or not longitude:
            return jsonify({'error': 'Coordinates required'}), 400
        
        # Simple distance calculation (Haversine formula)
        stores = db.session.execute(
            text('''
                SELECT id, store_name, city, state, phone, latitude, longitude,
                       (3959 * acos(cos(radians(:lat)) * cos(radians(latitude)) *
                       cos(radians(longitude) - radians(:lng)) +
                       sin(radians(:lat)) * sin(radians(latitude)))) AS distance
                FROM store_locations
                WHERE is_active = true
                ORDER BY distance
                LIMIT :limit
            '''),
            {'lat': latitude, 'lng': longitude, 'limit': limit}
        ).fetchall()
        
        stores_list = [
            {
                'id': str(s[0]),
                'store_name': s[1],
                'city': s[2],
                'state': s[3],
                'phone': s[4],
                'coordinates': {
                    'latitude': s[5],
                    'longitude': s[6]
                },
                'distance_miles': round(s[7], 2)
            } for s in stores
        ]
        
        return jsonify({'stores': stores_list}), 200
        
    except Exception as e:
        logger.error(f'Get nearest stores error: {str(e)}')
        return jsonify({'error': 'Failed to find nearest stores'}), 500
