from flask import Blueprint, request, jsonify
from extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
products_bp = Blueprint('products', __name__)

# ============================================================
# Products Endpoints
# ============================================================

@products_bp.route('', methods=['GET'])
def get_products():
    """List all products with pagination and filtering"""
    try:
        # Query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        category_id = request.args.get('category_id', type=str)
        search = request.args.get('search', type=str)
        sort_by = request.args.get('sort_by', 'created_at', type=str)
        
        # Build query
        query = 'SELECT * FROM products WHERE is_active = true'
        params = {}
        
        if category_id:
            query += ' AND category_id = :category_id'
            params['category_id'] = category_id
        
        if search:
            query += ' AND (title ILIKE :search OR description ILIKE :search)'
            params['search'] = f'%{search}%'
        
        # Sorting
        if sort_by == 'price_asc':
            query += ' ORDER BY price ASC'
        elif sort_by == 'price_desc':
            query += ' ORDER BY price DESC'
        elif sort_by == 'rating':
            query += ' ORDER BY rating DESC'
        else:
            query += ' ORDER BY created_at DESC'
        
        # Pagination
        offset = (page - 1) * limit
        query += ' LIMIT :limit OFFSET :offset'
        params['limit'] = limit
        params['offset'] = offset
        
        # Execute query
        products = db.session.execute(text(query), params).fetchall()
        
        # Get total count
        count_query = 'SELECT COUNT(*) FROM products WHERE is_active = true'
        count_params = {}
        
        if category_id:
            count_query += ' AND category_id = :category_id'
            count_params['category_id'] = category_id
        
        if search:
            count_query += ' AND (title ILIKE :search OR description ILIKE :search)'
            count_params['search'] = f'%{search}%'
        
        total = db.session.execute(text(count_query), count_params).scalar()
        
        # Format response
        products_list = []
        for p in products:
            products_list.append({
                'id': str(p[0]),
                'title': p[1],
                'slug': p[2],
                'sku': p[3],
                'category_id': str(p[4]),
                'price': float(p[5]),
                'original_price': float(p[6]) if p[6] else None,
                'discount_percent': float(p[7]) if p[7] else None,
                'short_description': p[8],
                'color': p[11],
                'rating': float(p[12]),
                'reviews_count': p[13],
                'is_best_seller': p[14],
                'is_featured': p[15],
                'is_new': p[16],
                'in_stock': p[17]
            })
        
        return jsonify({
            'products': products_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Get products error: {str(e)}')
        return jsonify({'error': 'Failed to fetch products'}), 500


@products_bp.route('/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get single product details"""
    try:
        # Get product
        product = db.session.execute(
            text('''
                SELECT p.*, ps.welt_type, ps.leather_type, ps.sole_type, ps.last_name,
                       ps.lining_material, ps.crafting_time_hours, ps.is_resolable, ps.origin_location
                FROM products p
                LEFT JOIN product_specifications ps ON p.id = ps.product_id
                WHERE p.id = :id AND p.is_active = true
            '''),
            {'id': product_id}
        ).fetchone()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Get images
        images = db.session.execute(
            text('''
                SELECT id, image_url, alt_text, display_order, is_primary
                FROM product_images
                WHERE product_id = :product_id
                ORDER BY display_order
            '''),
            {'product_id': product_id}
        ).fetchall()
        
        # Get sizes
        sizes = db.session.execute(
            text('''
                SELECT size, stock_quantity
                FROM product_sizes
                WHERE product_id = :product_id
            '''),
            {'product_id': product_id}
        ).fetchall()
        
        # Format response
        product_data = {
            'id': str(product[0]),
            'title': product[1],
            'slug': product[2],
            'sku': product[3],
            'category_id': str(product[4]),
            'price': float(product[5]),
            'original_price': float(product[6]) if product[6] else None,
            'discount_percent': float(product[7]) if product[7] else None,
            'short_description': product[8],
            'description': product[9],
            'color': product[11],
            'color_hex': product[12],
            'rating': float(product[13]),
            'reviews_count': product[14],
            'is_best_seller': product[15],
            'is_featured': product[16],
            'is_new': product[17],
            'in_stock': product[18],
            'specifications': {
                'welt_type': product[28],
                'leather_type': product[29],
                'sole_type': product[30],
                'last_name': product[31],
                'lining_material': product[32],
                'crafting_time_hours': product[33],
                'is_resolable': product[35],
                'origin_location': product[36]
            },
            'images': [
                {
                    'id': str(img[0]),
                    'url': img[1],
                    'alt_text': img[2],
                    'is_primary': img[4]
                } for img in images
            ],
            'sizes': {size[0]: size[1] for size in sizes}
        }
        
        return jsonify(product_data), 200
        
    except Exception as e:
        logger.error(f'Get product error: {str(e)}')
        return jsonify({'error': 'Failed to fetch product'}), 500


@products_bp.route('/by-slug/<slug>', methods=['GET'])
def get_product_by_slug(slug):
    """Get product by slug"""
    try:
        product = db.session.execute(
            text('SELECT id FROM products WHERE slug = :slug AND is_active = true'),
            {'slug': slug}
        ).fetchone()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Redirect to get_product
        return get_product(str(product[0]))
        
    except Exception as e:
        logger.error(f'Get product by slug error: {str(e)}')
        return jsonify({'error': 'Failed to fetch product'}), 500


@products_bp.route('/search', methods=['GET'])
def search_products():
    """Search products"""
    try:
        query = request.args.get('q', '', type=str)
        
        if not query or len(query) < 2:
            return jsonify({'error': 'Search query too short'}), 400
        
        products = db.session.execute(
            text('''
                SELECT id, title, slug, price, rating, color
                FROM products
                WHERE is_active = true AND (title ILIKE :search OR description ILIKE :search)
                LIMIT 20
            '''),
            {'search': f'%{query}%'}
        ).fetchall()
        
        products_list = [
            {
                'id': str(p[0]),
                'title': p[1],
                'slug': p[2],
                'price': float(p[3]),
                'rating': float(p[4]),
                'color': p[5]
            } for p in products
        ]
        
        return jsonify({'results': products_list}), 200
        
    except Exception as e:
        logger.error(f'Search error: {str(e)}')
        return jsonify({'error': 'Search failed'}), 500


@products_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all product categories"""
    try:
        categories = db.session.execute(
            text('''
                SELECT id, name, slug, description, image_url, display_order
                FROM categories
                WHERE is_active = true
                ORDER BY display_order
            ''')
        ).fetchall()
        
        categories_list = [
            {
                'id': str(c[0]),
                'name': c[1],
                'slug': c[2],
                'description': c[3],
                'image_url': c[4]
            } for c in categories
        ]
        
        return jsonify({'categories': categories_list}), 200
        
    except Exception as e:
        logger.error(f'Get categories error: {str(e)}')
        return jsonify({'error': 'Failed to fetch categories'}), 500
