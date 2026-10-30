from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
import bcrypt
import logging

from extensions import db
from services import serialize_user
from utils import clean_str, error, execute, is_uuid, json_body, query_one, split_name

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

MIN_PASSWORD_LENGTH = 6
USER_COLUMNS = '''id, email, first_name, last_name, phone, avatar_url, newsletter_subscribed,
                  promotions_enabled, preferred_shoe_size, preferred_width, is_admin, is_active, created_at'''


def _hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _auth_response(message, user, status):
    return jsonify({
        'message': message,
        'user': serialize_user(user),
        'access_token': create_access_token(identity=str(user['id'])),
    }), status


def _reset_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='password-reset')


# ============================================================
# Authentication Endpoints
# ============================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """Create new user account"""
    try:
        data = json_body()

        email = clean_str(data.get('email')).lower()
        password = data.get('password') or ''
        if not email or not password:
            return error('Email and password are required')

        first_name = clean_str(data.get('first_name'))
        last_name = clean_str(data.get('last_name'))
        if not first_name and data.get('name'):
            # The frontend store registers customers with a single full-name field
            first_name, last_name = split_name(data['name'])
        elif not last_name:
            return error('First name and last name are required')
        if not first_name:
            return error('First name and last name are required')

        if len(password) < MIN_PASSWORD_LENGTH:
            return error(f'Password must be at least {MIN_PASSWORD_LENGTH} characters')

        if query_one('SELECT id FROM users WHERE email = :email', email=email):
            return error('Email already registered')

        user = query_one(
            f'''INSERT INTO users (email, password_hash, first_name, last_name, phone, preferred_shoe_size, is_active)
                VALUES (:email, :password_hash, :first_name, :last_name, :phone,
                        COALESCE(:shoe_size, 'UK 8.5'), true)
                RETURNING {USER_COLUMNS}''',
            email=email, password_hash=_hash_password(password), first_name=first_name, last_name=last_name,
            phone=clean_str(data.get('phone')) or None,
            shoe_size=clean_str(data.get('preferred_shoe_size')) or None,
        )
        db.session.commit()
        return _auth_response('User created successfully', user, 201)

    except Exception as e:
        db.session.rollback()
        logger.error(f'Registration error: {str(e)}')
        return error('Registration failed', 500)


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = json_body()
        email = clean_str(data.get('email')).lower()
        password = data.get('password') or ''
        if not email or not password:
            return error('Email and password are required')

        user = query_one(f'SELECT {USER_COLUMNS}, password_hash FROM users WHERE email = :email', email=email)
        if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return error('Invalid email or password', 401)
        if not user['is_active']:
            return error('This account has been suspended', 403)

        execute('UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = :id', id=user['id'])
        db.session.commit()
        return _auth_response('Login successful', user, 200)

    except Exception as e:
        db.session.rollback()
        logger.error(f'Login error: {str(e)}')
        return error('Login failed', 500)


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user profile"""
    try:
        user = query_one(
            f'SELECT {USER_COLUMNS} FROM users WHERE id = :id AND is_active = true', id=get_jwt_identity())
        if not user:
            return error('User not found', 404)
        return jsonify({'user': serialize_user(user)}), 200

    except Exception as e:
        logger.error(f'Get user error: {str(e)}')
        return error('Failed to fetch user', 500)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True)
def logout():
    """User logout (JWTs are stateless; the client discards the token)"""
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change password for the logged-in user"""
    try:
        data = json_body()
        current = data.get('current_password') or ''
        new = data.get('new_password') or ''
        if len(new) < MIN_PASSWORD_LENGTH:
            return error(f'Password must be at least {MIN_PASSWORD_LENGTH} characters')

        user = query_one('SELECT password_hash FROM users WHERE id = :id', id=get_jwt_identity())
        if not user or not bcrypt.checkpw(current.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return error('Current password is incorrect', 401)

        execute('UPDATE users SET password_hash = :hash, updated_at = CURRENT_TIMESTAMP WHERE id = :id',
                hash=_hash_password(new), id=get_jwt_identity())
        db.session.commit()
        return jsonify({'message': 'Password changed successfully'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Change password error: {str(e)}')
        return error('Failed to change password', 500)


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    try:
        email = clean_str(json_body().get('email')).lower()
        if not email:
            return error('Email is required')

        response = {'message': 'If the email exists, a password reset link has been sent'}

        user = query_one('SELECT id, password_hash FROM users WHERE email = :email AND is_active = true', email=email)
        if user:
            # The hash fragment makes the token single-use: it stops verifying once the password changes
            token = _reset_serializer().dumps({'id': str(user['id']), 'v': user['password_hash'][-10:]})
            link = f'{current_app.config["FRONTEND_URL"]}/reset-password?token={token}'
            logger.info(f'Password reset link for {email}: {link}')  # TODO: send through an email provider
            if current_app.config.get('DEBUG'):
                response['reset_token'] = token  # lets developers test without an email service

        # Same answer for unknown emails so accounts cannot be enumerated
        return jsonify(response), 200

    except Exception as e:
        logger.error(f'Forgot password error: {str(e)}')
        return error('Failed to process request', 500)


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    try:
        data = json_body()
        token = data.get('token') or ''
        password = data.get('password') or ''
        if not token or not password:
            return error('Token and password are required')
        if len(password) < MIN_PASSWORD_LENGTH:
            return error(f'Password must be at least {MIN_PASSWORD_LENGTH} characters')

        try:
            payload = _reset_serializer().loads(token, max_age=current_app.config['PASSWORD_RESET_MAX_AGE'])
        except SignatureExpired:
            return error('Reset link has expired')
        except BadSignature:
            return error('Invalid reset link')

        if not is_uuid(payload.get('id')):
            return error('Invalid reset link')
        user = query_one('SELECT id, password_hash FROM users WHERE id = :id AND is_active = true', id=payload['id'])
        if not user or user['password_hash'][-10:] != payload.get('v'):
            return error('Invalid or already used reset link')

        execute('UPDATE users SET password_hash = :hash, updated_at = CURRENT_TIMESTAMP WHERE id = :id',
                hash=_hash_password(password), id=user['id'])
        db.session.commit()
        return jsonify({'message': 'Password reset successful'}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'Reset password error: {str(e)}')
        return error('Failed to reset password', 500)
