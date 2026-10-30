from flask import Blueprint, jsonify, request
import logging

from services import serialize_store, store_hours_by_day
from utils import error, is_uuid, query_all, query_one

logger = logging.getLogger(__name__)
stores_bp = Blueprint('stores', __name__)

# ============================================================
# Store Locations Endpoints
# ============================================================

def _serialize(rows):
    rows = list(rows)
    hours = store_hours_by_day([r['id'] for r in rows])
    return [serialize_store(r, hours.get(r['id'])) for r in rows]


@stores_bp.route('', methods=['GET'])
def get_stores():
    """Get all active store locations"""
    try:
        rows = query_all('SELECT * FROM store_locations WHERE is_active = true ORDER BY city, name')
        return jsonify({'stores': _serialize(rows)}), 200

    except Exception as e:
        logger.error(f'Get stores error: {str(e)}')
        return error('Failed to fetch stores', 500)


@stores_bp.route('/search', methods=['GET'])
def search_stores():
    """Search stores by city, state, country or name"""
    try:
        query = request.args.get('q', '', type=str).strip()
        if len(query) < 2:
            return error('Search query too short')

        rows = query_all(
            '''SELECT * FROM store_locations
               WHERE is_active = true AND (city ILIKE :s OR state ILIKE :s OR country ILIKE :s OR name ILIKE :s)
               ORDER BY city, name''', s=f'%{query}%')
        return jsonify({'results': _serialize(rows)}), 200

    except Exception as e:
        logger.error(f'Search stores error: {str(e)}')
        return error('Failed to search stores', 500)


@stores_bp.route('/nearest', methods=['GET'])
def get_nearest_stores():
    """Stores nearest to a coordinate (great-circle distance)"""
    try:
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        limit = min(max(request.args.get('limit', 5, type=int) or 5, 1), 50)

        if latitude is None or longitude is None:
            return error('Coordinates required')

        rows = query_all(
            '''SELECT *, (3959 * acos(LEAST(1.0, GREATEST(-1.0,
                          cos(radians(:lat)) * cos(radians(latitude)) * cos(radians(longitude) - radians(:lng))
                          + sin(radians(:lat)) * sin(radians(latitude)))))) AS distance_miles
               FROM store_locations
               WHERE is_active = true AND latitude IS NOT NULL AND longitude IS NOT NULL
               ORDER BY distance_miles LIMIT :limit''',
            lat=latitude, lng=longitude, limit=limit)

        stores = _serialize(rows)
        for store, row in zip(stores, rows):
            store['distance_miles'] = round(float(row['distance_miles']), 2)
        return jsonify({'stores': stores}), 200

    except Exception as e:
        logger.error(f'Get nearest stores error: {str(e)}')
        return error('Failed to find nearest stores', 500)


@stores_bp.route('/<store_id>', methods=['GET'])
def get_store(store_id):
    """Get store details with opening hours"""
    try:
        if not is_uuid(store_id):
            return error('Store not found', 404)
        store = query_one('SELECT * FROM store_locations WHERE id = :id AND is_active = true', id=store_id)
        if not store:
            return error('Store not found', 404)
        return jsonify(_serialize([store])[0]), 200

    except Exception as e:
        logger.error(f'Get store error: {str(e)}')
        return error('Failed to fetch store', 500)
