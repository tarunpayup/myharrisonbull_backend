from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()

def init_db(app):
    """Initialize database"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

def init_jwt(app):
    """Initialize JWT"""
    jwt.init_app(app)

def init_cors(app, config):
    """Initialize CORS"""
    CORS(app, origins=config.CORS_ORIGINS)
