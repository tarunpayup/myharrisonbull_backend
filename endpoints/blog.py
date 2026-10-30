from flask import Blueprint, jsonify, request
import logging

from services import BLOG_SELECT, serialize_blog_post
from utils import error, is_uuid, pagination, paging, query_all, query_one, query_scalar

logger = logging.getLogger(__name__)
blog_bp = Blueprint('blog', __name__)

# ============================================================
# Blog Endpoints
# ============================================================

@blog_bp.route('', methods=['GET'])
def get_blog_posts():
    """Get published blog posts"""
    try:
        page, limit, offset = paging()
        where, params = ['b.is_published = true'], {}

        category = request.args.get('category')
        if category:
            where.append('LOWER(b.category) = LOWER(:category)')
            params['category'] = category

        search = request.args.get('search')
        if search:
            where.append('(b.title ILIKE :search OR b.content ILIKE :search OR b.excerpt ILIKE :search)')
            params['search'] = f'%{search}%'
        clause = ' AND '.join(where)

        rows = query_all(
            f'''{BLOG_SELECT} WHERE {clause}
                ORDER BY b.published_at DESC NULLS LAST, b.created_at DESC LIMIT :limit OFFSET :offset''',
            limit=limit, offset=offset, **params)
        total = query_scalar(f'SELECT COUNT(*) FROM blog_posts b WHERE {clause}', **params)

        return jsonify({
            'posts': [serialize_blog_post(p) for p in rows],
            'pagination': pagination(page, limit, total),
        }), 200

    except Exception as e:
        logger.error(f'Get blog posts error: {str(e)}')
        return error('Failed to fetch blog posts', 500)


@blog_bp.route('/categories', methods=['GET'])
def get_blog_categories():
    """Get blog categories"""
    try:
        rows = query_all(
            '''SELECT DISTINCT category FROM blog_posts
               WHERE is_published = true AND category IS NOT NULL ORDER BY category''')
        return jsonify({'categories': [r['category'] for r in rows]}), 200

    except Exception as e:
        logger.error(f'Get blog categories error: {str(e)}')
        return error('Failed to fetch categories', 500)


@blog_bp.route('/by-slug/<slug>', methods=['GET'])
def get_blog_post_by_slug(slug):
    """Get blog post by slug"""
    try:
        post = query_one(f'{BLOG_SELECT} WHERE b.slug = :slug AND b.is_published = true', slug=slug)
        if not post:
            return error('Blog post not found', 404)
        return jsonify(serialize_blog_post(post)), 200

    except Exception as e:
        logger.error(f'Get blog post by slug error: {str(e)}')
        return error('Failed to fetch blog post', 500)


@blog_bp.route('/related/<post_id>', methods=['GET'])
def get_related_posts(post_id):
    """Other posts from the same category"""
    try:
        if not is_uuid(post_id):
            return error('Blog post not found', 404)
        post = query_one('SELECT id, category FROM blog_posts WHERE id = :id', id=post_id)
        if not post:
            return error('Blog post not found', 404)

        related = query_all(
            f'''{BLOG_SELECT}
                WHERE b.category IS NOT DISTINCT FROM :category AND b.id <> :id AND b.is_published = true
                ORDER BY b.published_at DESC NULLS LAST LIMIT 5''',
            category=post['category'], id=post_id)

        return jsonify({'related_posts': [serialize_blog_post(p, with_content=False) for p in related]}), 200

    except Exception as e:
        logger.error(f'Get related posts error: {str(e)}')
        return error('Failed to fetch related posts', 500)


@blog_bp.route('/<post_ref>', methods=['GET'])
def get_blog_post(post_ref):
    """Get single blog post by id (a slug is accepted too)"""
    try:
        column = 'id' if is_uuid(post_ref) else 'slug'
        post = query_one(f'{BLOG_SELECT} WHERE b.{column} = :ref AND b.is_published = true', ref=post_ref)
        if not post:
            return error('Blog post not found', 404)
        return jsonify(serialize_blog_post(post)), 200

    except Exception as e:
        logger.error(f'Get blog post error: {str(e)}')
        return error('Failed to fetch blog post', 500)
