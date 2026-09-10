from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from extensions import db
from sqlalchemy import text
import bcrypt
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

# ============================================================
# Authentication Endpoints
# ============================================================

@auth_bp.route('/register', methods=['POST'])
def register():
    """Create new user account"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data.get('email').strip().lower()
        password = data.get('password')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        if not first_name or not last_name:
            return jsonify({'error': 'First name and last name are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user exists
        result = db.session.execute(
            text('SELECT id FROM users WHERE email = :email'),
            {'email': email}
        ).fetchone()
        
        if result:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        db.session.execute(
            text('''
                INSERT INTO users (email, password_hash, first_name, last_name, is_active)
                VALUES (:email, :password_hash, :first_name, :last_name, true)
            '''),
            {
                'email': email,
                'password_hash': password_hash,
                'first_name': first_name,
                'last_name': last_name
            }
        )
        db.session.commit()
        
        # Get user ID
        user = db.session.execute(
            text('SELECT id, email, first_name, last_name FROM users WHERE email = :email'),
            {'email': email}
        ).fetchone()
        
        # Create token
        access_token = create_access_token(identity=str(user[0]))
        
        return jsonify({
            'message': 'User created successfully',
            'user': {
                'id': str(user[0]),
                'email': user[1],
                'first_name': user[2],
                'last_name': user[3]
            },
            'access_token': access_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f'Registration error: {str(e)}')
        return jsonify({'error': 'Registration failed'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        email = data.get('email').strip().lower()
        password = data.get('password')
        
        # Get user
        user = db.session.execute(
            text('''
                SELECT id, email, first_name, last_name, password_hash, is_active, is_admin
                FROM users WHERE email = :email AND is_active = true
            '''),
            {'email': email}
        ).fetchone()
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user[5].encode('utf-8')):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Update last login
        db.session.execute(
            text('UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = :id'),
            {'id': user[0]}
        )
        db.session.commit()
        
        # Create token
        access_token = create_access_token(identity=str(user[0]))
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': str(user[0]),
                'email': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'is_admin': user[6]
            },
            'access_token': access_token
        }), 200
        
    except Exception as e:
        logger.error(f'Login error: {str(e)}')
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        
        user = db.session.execute(
            text('''
                SELECT id, email, first_name, last_name, phone, avatar_url,
                       newsletter_subscribed, promotions_enabled, is_admin, created_at
                FROM users WHERE id = :id AND is_active = true
            '''),
            {'id': user_id}
        ).fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': {
                'id': str(user[0]),
                'email': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'phone': user[4],
                'avatar_url': user[5],
                'newsletter_subscribed': user[6],
                'promotions_enabled': user[7],
                'is_admin': user[8],
                'created_at': str(user[9])
            }
        }), 200
        
    except Exception as e:
        logger.error(f'Get user error: {str(e)}')
        return jsonify({'error': 'Failed to fetch user'}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout"""
    # JWT is stateless, so just return success
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset"""
    try:
        data = request.get_json()
        
        if not data or not data.get('email'):
            return jsonify({'error': 'Email is required'}), 400
        
        email = data.get('email').strip().lower()
        
        # Check if user exists
        user = db.session.execute(
            text('SELECT id FROM users WHERE email = :email'),
            {'email': email}
        ).fetchone()
        
        if not user:
            # Don't reveal if email exists (security)
            return jsonify({'message': 'If email exists, password reset link will be sent'}), 200
        
        # TODO: Generate reset token and send email
        # For now, just return success
        
        return jsonify({'message': 'Password reset link sent to email'}), 200
        
    except Exception as e:
        logger.error(f'Forgot password error: {str(e)}')
        return jsonify({'error': 'Failed to process request'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password with token"""
    try:
        data = request.get_json()
        
        if not data or not data.get('token') or not data.get('password'):
            return jsonify({'error': 'Token and password are required'}), 400
        
        # TODO: Validate token and update password
        
        return jsonify({'message': 'Password reset successful'}), 200
        
    except Exception as e:
        logger.error(f'Reset password error: {str(e)}')
        return jsonify({'error': 'Failed to reset password'}), 500
