from flask import Blueprint, request, jsonify
from extensions import db
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)
blog_bp = Blueprint('blog', __name__)

# ============================================================
# Blog Endpoints
# ============================================================

@blog_bp.route('', methods=['GET'])
def get_blog_posts():
    """Get blog posts"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        category = request.args.get('category', type=str)
        search = request.args.get('search', type=str)
        
        offset = (page - 1) * limit
        
        # Build query
        query = 'SELECT * FROM blog_posts WHERE is_published = true'
        params = {}
        
        if category:
            query += ' AND category = :category'
            params['category'] = category
        
        if search:
            query += ' AND (title ILIKE :search OR content ILIKE :search)'
            params['search'] = f'%{search}%'
        
        query += ' ORDER BY published_at DESC LIMIT :limit OFFSET :offset'
        params['limit'] = limit
        params['offset'] = offset
        
        posts = db.session.execute(text(query), params).fetchall()
        
        # Get total count
        count_query = 'SELECT COUNT(*) FROM blog_posts WHERE is_published = true'
        count_params = {}
        
        if category:
            count_query += ' AND category = :category'
            count_params['category'] = category
        
        if search:
            count_query += ' AND (title ILIKE :search OR content ILIKE :search)'
            count_params['search'] = f'%{search}%'
        
        total = db.session.execute(text(count_query), count_params).scalar()
        
        posts_list = []
        for p in posts:
            posts_list.append({
                'id': str(p[0]),
                'title': p[1],
                'slug': p[2],
                'category': p[3],
                'excerpt': p[4],
                'featured_image': p[5],
                'author': p[6],
                'view_count': p[7],
                'published_at': str(p[8]),
                'updated_at': str(p[9])
            })
        
        return jsonify({
            'posts': posts_list,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Get blog posts error: {str(e)}')
        return jsonify({'error': 'Failed to fetch blog posts'}), 500


@blog_bp.route('/<post_id>', methods=['GET'])
def get_blog_post(post_id):
    """Get single blog post"""
    try:
        post = db.session.execute(
            text('''
                SELECT id, title, slug, category, excerpt, content, featured_image,
                       author, view_count, published_at, updated_at
                FROM blog_posts
                WHERE id = :id AND is_published = true
            '''),
            {'id': post_id}
        ).fetchone()
        
        if not post:
            return jsonify({'error': 'Blog post not found'}), 404
        
        # Increment view count
        db.session.execute(
            text('UPDATE blog_posts SET view_count = view_count + 1 WHERE id = :id'),
            {'id': post_id}
        )
        db.session.commit()
        
        post_data = {
            'id': str(post[0]),
            'title': post[1],
            'slug': post[2],
            'category': post[3],
            'excerpt': post[4],
            'content': post[5],
            'featured_image': post[6],
            'author': post[7],
            'view_count': post[8] + 1,
            'published_at': str(post[9]),
            'updated_at': str(post[10])
        }
        
        return jsonify(post_data), 200
        
    except Exception as e:
        logger.error(f'Get blog post error: {str(e)}')
        return jsonify({'error': 'Failed to fetch blog post'}), 500


@blog_bp.route('/by-slug/<slug>', methods=['GET'])
def get_blog_post_by_slug(slug):
    """Get blog post by slug"""
    try:
        post = db.session.execute(
            text('SELECT id FROM blog_posts WHERE slug = :slug AND is_published = true'),
            {'slug': slug}
        ).fetchone()
        
        if not post:
            return jsonify({'error': 'Blog post not found'}), 404
        
        return get_blog_post(str(post[0]))
        
    except Exception as e:
        logger.error(f'Get blog post by slug error: {str(e)}')
        return jsonify({'error': 'Failed to fetch blog post'}), 500


@blog_bp.route('/categories', methods=['GET'])
def get_blog_categories():
    """Get blog categories"""
    try:
        categories = db.session.execute(
            text('''
                SELECT DISTINCT category FROM blog_posts
                WHERE is_published = true
                ORDER BY category
            ''')
        ).fetchall()
        
        return jsonify({
            'categories': [c[0] for c in categories]
        }), 200
        
    except Exception as e:
        logger.error(f'Get blog categories error: {str(e)}')
        return jsonify({'error': 'Failed to fetch categories'}), 500


@blog_bp.route('/related/<post_id>', methods=['GET'])
def get_related_posts(post_id):
    """Get related blog posts"""
    try:
        # Get category of current post
        post = db.session.execute(
            text('SELECT category FROM blog_posts WHERE id = :id'),
            {'id': post_id}
        ).fetchone()
        
        if not post:
            return jsonify({'error': 'Blog post not found'}), 404
        
        category = post[0]
        
        # Get related posts from same category
        related = db.session.execute(
            text('''
                SELECT id, title, slug, excerpt, featured_image, view_count
                FROM blog_posts
                WHERE category = :category AND id != :id AND is_published = true
                ORDER BY view_count DESC
                LIMIT 5
            '''),
            {'category': category, 'id': post_id}
        ).fetchall()
        
        posts_list = [
            {
                'id': str(r[0]),
                'title': r[1],
                'slug': r[2],
                'excerpt': r[3],
                'featured_image': r[4],
                'view_count': r[5]
            } for r in related
        ]
        
        return jsonify({'related_posts': posts_list}), 200
        
    except Exception as e:
        logger.error(f'Get related posts error: {str(e)}')
        return jsonify({'error': 'Failed to fetch related posts'}), 500
