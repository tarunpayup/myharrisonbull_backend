from flask import Flask, jsonify
from config import get_config
from extensions import db, jwt, init_db, init_jwt, init_cors
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Flask application factory"""
    
    # Get configuration
    config = get_config()
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Initialize extensions
    init_db(app)
    init_jwt(app)
    init_cors(app, config)
    
    # Register blueprints
    from endpoints.auth import auth_bp
    from endpoints.products import products_bp
    from endpoints.orders import orders_bp
    from endpoints.users import users_bp
    from endpoints.reviews import reviews_bp
    from endpoints.coupons import coupons_bp
    from endpoints.blog import blog_bp
    from endpoints.stores import stores_bp
    from endpoints.admin import admin_bp
    from endpoints.health import health_bp
    from endpoints.content import banners_bp, site_bp, contact_bp, notifications_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(orders_bp, url_prefix='/api/orders')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(reviews_bp, url_prefix='/api/reviews')
    app.register_blueprint(coupons_bp, url_prefix='/api/coupons')
    app.register_blueprint(blog_bp, url_prefix='/api/blog')
    app.register_blueprint(stores_bp, url_prefix='/api/stores')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(banners_bp, url_prefix='/api/banners')
    app.register_blueprint(site_bp, url_prefix='/api/site-content')
    app.register_blueprint(contact_bp, url_prefix='/api/contact')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(health_bp, url_prefix='/health')
    # The frontend docs probe /api/health, so serve the same checks there too
    app.register_blueprint(health_bp, url_prefix='/api/health', name='api_health')
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            'name': 'Harrison Bull E-Commerce API',
            'version': '1.0.0',
            'status': 'active',
            'docs': 'See API_DOCUMENTATION.md',
            'health': '/health'
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed'}), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'Internal error: {error}')
        return jsonify({'error': 'Internal server error'}), 500
    
    return app


# Create app instance for Gunicorn
app = create_app()

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False))
