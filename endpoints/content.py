"""Public content endpoints: promotional banners, CMS site content, contact form, notifications."""
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
import logging

from extensions import db
from services import serialize_banner
from utils import clean_str, error, execute, is_uuid, json_body, query_all, query_one

logger = logging.getLogger(__name__)
banners_bp = Blueprint('banners', __name__)
site_bp = Blueprint('site', __name__)
contact_bp = Blueprint('contact', __name__)
notifications_bp = Blueprint('notifications', __name__)

# ------------------------------------------------------------
# Banners
# ------------------------------------------------------------

@banners_bp.route('', methods=['GET'])
def get_banners():
    """Active promotional banners that are inside their date window"""
    try:
        rows = query_all(
            '''SELECT * FROM promotional_banners
               WHERE is_active = true
                 AND (start_date IS NULL OR start_date <= CURRENT_TIMESTAMP)
                 AND (end_date IS NULL OR end_date >= CURRENT_TIMESTAMP)
               ORDER BY display_order, created_at DESC''')
        return jsonify({'banners': [serialize_banner(b) for b in rows]}), 200

    except Exception as e:
        logger.error(f'Get banners error: {str(e)}')
        return error('Failed to fetch banners', 500)


# ------------------------------------------------------------
# Site content (navbar / footer / page sections edited in the admin CMS)
# ------------------------------------------------------------

@site_bp.route('', methods=['GET'])
def get_site_content():
    """Returns the saved SiteContent blob, or null so the frontend falls back to its defaults"""
    try:
        row = query_one("SELECT value FROM site_settings WHERE key = 'site_content'")
        return jsonify({'content': row['value'] if row else None}), 200

    except Exception as e:
        logger.error(f'Get site content error: {str(e)}')
        return error('Failed to fetch site content', 500)


# ------------------------------------------------------------
# Contact form
# ------------------------------------------------------------

@contact_bp.route('', methods=['POST'])
def submit_contact():
    """Store a contact form message"""
    try:
        data = json_body()
        name, email = clean_str(data.get('name')), clean_str(data.get('email'))
        message = clean_str(data.get('message'))
        if not name or not email or not message:
            return error('Name, email and message are required')
        if '@' not in email:
            return error('A valid email is required')

        execute(
            'INSERT INTO contact_messages (name, email, subject, message) VALUES (:name, :email, :subject, :message)',
            name=name[:255], email=email[:255], subject=clean_str(data.get('subject'))[:255] or None,
            message=message[:5000])
        db.session.commit()

        return jsonify({'message': 'Thank you, your message has been received.'}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f'Contact form error: {str(e)}')
        return error('Failed to send message', 500)


# ------------------------------------------------------------
# Notifications (customers and admins each read their own)
# ------------------------------------------------------------

def _serialize_notification(n):
    return {
        'id': str(n['id']),
        'title': n['title'],
        'message': n['message'],
        'timestamp': n['created_at'].isoformat() if n['created_at'] else None,
        'type': n['notification_type'],
        'read': bool(n['is_read']),
        'order_id': str(n['related_order_id']) if n['related_order_id'] else None,
    }


@notifications_bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    try:
        rows = query_all(
            'SELECT * FROM notifications WHERE user_id = :u ORDER BY created_at DESC LIMIT 100', u=get_jwt_identity())
        return jsonify({
            'notifications': [_serialize_notification(n) for n in rows],
            'unread_count': sum(1 for n in rows if not n['is_read']),
        }), 200

    except Exception as e:
        logger.error(f'Get notifications error: {str(e)}')
        return error('Failed to fetch notifications', 500)


@notifications_bp.route('/read-all', methods=['POST'])
@jwt_required()
def mark_all_read():
    try:
        execute('''UPDATE notifications SET is_read = true, read_at = CURRENT_TIMESTAMP
                   WHERE user_id = :u AND is_read = false''', u=get_jwt_identity())
        db.session.commit()
        return jsonify({'message': 'All notifications marked as read'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Mark all read error: {str(e)}')
        return error('Failed to update notifications', 500)


@notifications_bp.route('/<notification_id>/read', methods=['POST'])
@jwt_required()
def mark_read(notification_id):
    try:
        if not is_uuid(notification_id):
            return error('Notification not found', 404)
        result = execute('''UPDATE notifications SET is_read = true, read_at = CURRENT_TIMESTAMP
                            WHERE id = :id AND user_id = :u''', id=notification_id, u=get_jwt_identity())
        if result.rowcount == 0:
            return error('Notification not found', 404)
        db.session.commit()
        return jsonify({'message': 'Notification marked as read'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Mark read error: {str(e)}')
        return error('Failed to update notification', 500)


@notifications_bp.route('', methods=['DELETE'])
@jwt_required()
def clear_notifications():
    try:
        execute('DELETE FROM notifications WHERE user_id = :u', u=get_jwt_identity())
        db.session.commit()
        return jsonify({'message': 'Notifications cleared'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Clear notifications error: {str(e)}')
        return error('Failed to clear notifications', 500)
