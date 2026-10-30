from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()

def init_db(app):
    """Initialize database"""
    db.init_app(app)

def init_jwt(app):
    """Initialize JWT"""
    jwt.init_app(app)

    # The frontend reads `error` from every failed response, so make JWT failures match
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({'error': 'Authentication required'}), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify({'error': 'Invalid token'}), 401

    @jwt.expired_token_loader
    def expired_token(header, payload):
        return jsonify({'error': 'Token has expired'}), 401

def init_cors(app, config):
    """Initialize CORS"""
    CORS(
        app,
        resources={r'/*': {'origins': config.CORS_ORIGINS}},
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization'],
    )
