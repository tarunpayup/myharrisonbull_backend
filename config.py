import os
from dotenv import load_dotenv

load_dotenv()


def _database_url():
    url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/harrison_bull_db')
    # Render/Heroku hand out postgres:// URLs, which SQLAlchemy 2 no longer accepts
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


def _cors_origins():
    # FRONTEND_URL may hold several comma-separated origins
    origins = [o.strip().rstrip('/') for o in os.getenv('FRONTEND_URL', 'http://localhost:3000').split(',') if o.strip()]
    for local in ('http://localhost:3000', 'http://127.0.0.1:3000'):
        if local not in origins and os.getenv('FLASK_ENV', 'development') != 'production':
            origins.append(local)
    return origins


class Config:
    """Base configuration"""
    # Database
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DATABASE_POOL_MAX', 10)),
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }

    # Flask
    SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')

    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET', 'dev-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = 86400 * 7  # 7 days

    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', 5000))
    API_URL = os.getenv('API_URL', 'http://localhost:5000')

    # Frontend
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000').split(',')[0].strip()

    # CORS
    CORS_ORIGINS = _cors_origins()

    # Password reset links
    PASSWORD_RESET_MAX_AGE = 3600  # 1 hour

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
    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_ENGINE_OPTIONS = {}


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
