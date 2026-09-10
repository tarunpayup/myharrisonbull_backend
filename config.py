import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://localhost:5432/harrison_bull_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DATABASE_POOL_MAX', 10)),
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Flask
    SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', False)
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 86400 * 7  # 7 days
    
    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 5000))
    API_URL = os.getenv('API_URL', 'http://localhost:5000')
    
    # Frontend
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # CORS
    CORS_ORIGINS = [os.getenv('FRONTEND_URL', 'http://localhost:3000')]
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration dictionary
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
