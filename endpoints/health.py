from flask import Blueprint, jsonify
from extensions import db
from sqlalchemy import text
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
health_bp = Blueprint('health', __name__)

# ============================================================
# Health Check Endpoints
# ============================================================

@health_bp.route('', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    try:
        return jsonify({
            'status': 'healthy',
            'message': 'Harrison Bull API is running',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200
    except Exception as e:
        logger.error(f'Health check error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Health check failed'
        }), 500


@health_bp.route('/deep', methods=['GET'])
def deep_health_check():
    """Comprehensive health check with database connectivity test"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'services': {
                'api': 'ok',
                'database': 'checking...'
            }
        }
        
        # Test database connectivity
        try:
            result = db.session.execute(text('SELECT 1')).fetchone()
            if result:
                health_status['services']['database'] = 'ok'
            else:
                health_status['services']['database'] = 'error'
                health_status['status'] = 'degraded'
        except Exception as db_error:
            logger.error(f'Database health check failed: {str(db_error)}')
            health_status['services']['database'] = 'error'
            health_status['status'] = 'degraded'
        
        http_status = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), http_status
        
    except Exception as e:
        logger.error(f'Deep health check error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': 'Deep health check failed',
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check - API is ready to accept requests"""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        
        return jsonify({
            'ready': True,
            'message': 'API is ready to accept requests',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f'Readiness check failed: {str(e)}')
        return jsonify({
            'ready': False,
            'message': 'API is not ready',
            'error': str(e)
        }), 503


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """Liveness check - API process is running"""
    try:
        return jsonify({
            'alive': True,
            'message': 'API process is running',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f'Liveness check failed: {str(e)}')
        return jsonify({
            'alive': False,
            'message': 'API process check failed'
        }), 500
