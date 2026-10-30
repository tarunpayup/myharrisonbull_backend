"""Shared helpers for the endpoint modules."""
import re
import uuid
from decimal import Decimal
from functools import wraps

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from sqlalchemy import text

from extensions import db


# ------------------------------------------------------------
# Database helpers (named-column access instead of row indexes)
# ------------------------------------------------------------

def query_all(sql, **params):
    return db.session.execute(text(sql), params).mappings().all()


def query_one(sql, **params):
    return db.session.execute(text(sql), params).mappings().first()


def query_scalar(sql, **params):
    return db.session.execute(text(sql), params).scalar()


def execute(sql, **params):
    return db.session.execute(text(sql), params)


# ------------------------------------------------------------
# Value helpers
# ------------------------------------------------------------

def is_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def num(value):
    """Decimal -> float, None stays None"""
    return float(value) if value is not None else None


def iso(value):
    return value.isoformat() if value is not None else None


def money(value):
    return Decimal(str(value)).quantize(Decimal('0.01'))


def slugify(value):
    return re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')


def split_name(full_name):
    parts = (full_name or '').strip().split(None, 1)
    return (parts[0] if parts else ''), (parts[1] if len(parts) > 1 else '')


def clean_str(value, default=''):
    return value.strip() if isinstance(value, str) else default


def json_body():
    """Request JSON as a dict (never None)"""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


# ------------------------------------------------------------
# Responses / pagination
# ------------------------------------------------------------

def error(message, status=400, **extra):
    return jsonify({'error': message, **extra}), status


def paging(default_limit=10, max_limit=100):
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    limit = request.args.get('limit', default_limit, type=int) or default_limit
    limit = min(max(limit, 1), max_limit)
    return page, limit, (page - 1) * limit


def pagination(page, limit, total):
    return {
        'page': page,
        'limit': limit,
        'total': total,
        'pages': (total + limit - 1) // limit if limit else 0,
    }


# ------------------------------------------------------------
# Auth helpers
# ------------------------------------------------------------

def optional_user_id():
    """Identity of the caller, or None for guests."""
    verify_jwt_in_request(optional=True)
    return get_jwt_identity()


def is_admin_user(user_id):
    if not user_id or not is_uuid(user_id):
        return False
    return bool(query_scalar(
        'SELECT is_admin FROM users WHERE id = :id AND is_active = true', id=user_id
    ))


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        if not is_admin_user(get_jwt_identity()):
            return error('Admin access required', 403)
        return fn(*args, **kwargs)
    return wrapper
