from flask import Blueprint, request, jsonify
import logging

from services import PRODUCT_SELECT, get_product_rows, serialize_products
from utils import error, is_uuid, pagination, paging, query_all, query_scalar

logger = logging.getLogger(__name__)
products_bp = Blueprint('products', __name__)

SORTS = {
    'price_asc': 'p.price ASC',
    'price_desc': 'p.price DESC',
    'rating': 'p.rating DESC, p.reviews_count DESC',
    'newest': 'p.created_at DESC',
    'created_at': 'p.created_at DESC',
}

# ============================================================
# Products Endpoints
# ============================================================

@products_bp.route('', methods=['GET'])
def get_products():
    """List active products with pagination and filtering"""
    try:
        page, limit, offset = paging(default_limit=12, max_limit=100)
        args = request.args

        where = ['p.is_active = true']
        params = {}

        category_id = args.get('category_id')
        if category_id:
            if not is_uuid(category_id):
                return jsonify({'products': [], 'pagination': pagination(page, limit, 0)}), 200
            where.append('p.category_id = :category_id')
            params['category_id'] = category_id

        category = args.get('category')  # category name or slug, e.g. "Oxfords" / "monk-straps"
        if category:
            where.append('(LOWER(c.name) = LOWER(:category) OR c.slug = LOWER(:category))')
            params['category'] = category

        search = args.get('search')
        if search:
            where.append('(p.title ILIKE :search OR p.description ILIKE :search OR p.short_description ILIKE :search '
                         'OR p.color ILIKE :search OR c.name ILIKE :search)')
            params['search'] = f'%{search}%'

        for flag, column in (('featured', 'is_featured'), ('best_seller', 'is_best_seller'), ('new', 'is_new')):
            if args.get(flag, '').lower() in ('1', 'true'):
                where.append(f'p.{column} = true')
        if args.get('in_stock', '').lower() in ('1', 'true'):
            where.append('p.in_stock = true')

        for key, op in (('min_price', '>='), ('max_price', '<=')):
            value = args.get(key, type=float)
            if value is not None:
                where.append(f'p.price {op} :{key}')
                params[key] = value

        clause = ' AND '.join(where)
        order = SORTS.get(args.get('sort_by', 'newest'), SORTS['newest'])

        rows = query_all(
            f'{PRODUCT_SELECT} WHERE {clause} ORDER BY {order}, p.id LIMIT :limit OFFSET :offset',
            limit=limit, offset=offset, **params)
        total = query_scalar(
            f'SELECT COUNT(*) FROM products p JOIN categories c ON c.id = p.category_id WHERE {clause}', **params)

        return jsonify({
            'products': serialize_products(rows),
            'pagination': pagination(page, limit, total),
        }), 200

    except Exception as e:
        logger.error(f'Get products error: {str(e)}')
        return error('Failed to fetch products', 500)


@products_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all product categories"""
    try:
        categories = query_all(
            '''SELECT c.id, c.name, c.slug, c.description, c.image_url,
                      (SELECT COUNT(*) FROM products p WHERE p.category_id = c.id AND p.is_active = true) AS product_count
               FROM categories c WHERE c.is_active = true ORDER BY c.display_order, c.name''')

        return jsonify({'categories': [
            {
                'id': str(c['id']),
                'name': c['name'],
                'slug': c['slug'],
                'description': c['description'],
                'image_url': c['image_url'],
                'product_count': c['product_count'],
            } for c in categories
        ]}), 200

    except Exception as e:
        logger.error(f'Get categories error: {str(e)}')
        return error('Failed to fetch categories', 500)


@products_bp.route('/search', methods=['GET'])
def search_products():
    """Quick search used by the search modal"""
    try:
        query = request.args.get('q', '', type=str).strip()
        if len(query) < 2:
            return error('Search query too short')

        rows = query_all(
            f'''{PRODUCT_SELECT}
                WHERE p.is_active = true AND (p.title ILIKE :search OR p.description ILIKE :search
                      OR p.short_description ILIKE :search OR p.color ILIKE :search OR c.name ILIKE :search)
                ORDER BY p.is_best_seller DESC, p.rating DESC LIMIT 20''',
            search=f'%{query}%')

        return jsonify({'results': serialize_products(rows)}), 200

    except Exception as e:
        logger.error(f'Search error: {str(e)}')
        return error('Search failed', 500)


@products_bp.route('/by-slug/<slug>', methods=['GET'])
def get_product_by_slug(slug):
    """Get product by slug"""
    try:
        rows = get_product_rows('p.slug = :slug AND p.is_active = true', slug=slug)
        if not rows:
            return error('Product not found', 404)
        return jsonify(serialize_products(rows)[0]), 200

    except Exception as e:
        logger.error(f'Get product by slug error: {str(e)}')
        return error('Failed to fetch product', 500)


@products_bp.route('/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get a single product by id (a slug is accepted too, like the frontend store does)"""
    try:
        if is_uuid(product_id):
            rows = get_product_rows('p.id = :id AND p.is_active = true', id=product_id)
        else:
            rows = get_product_rows('p.slug = :slug AND p.is_active = true', slug=product_id)
        if not rows:
            return error('Product not found', 404)
        return jsonify(serialize_products(rows)[0]), 200

    except Exception as e:
        logger.error(f'Get product error: {str(e)}')
        return error('Failed to fetch product', 500)
