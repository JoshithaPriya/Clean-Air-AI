import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

def create_app():
    app = Flask(__name__)
    
    # Enable CORS for local development. In production, this should be restricted.
    CORS(app)
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'success',
            'message': 'Backend is running!',
            'phase': 'Phase 1D'
        }), 200

    # Register Blueprints
    from routes.air_quality import air_quality_bp
    from routes.weather import weather_bp
    from routes.era5 import era5_bp
    from routes.gfs import gfs_bp
    from routes.earth_engine import earth_engine_bp
    
    app.register_blueprint(air_quality_bp, url_prefix='/api/air-quality')
    app.register_blueprint(weather_bp, url_prefix='/api/weather')
    app.register_blueprint(era5_bp, url_prefix='/api/weather/era5')
    app.register_blueprint(gfs_bp, url_prefix='/api/weather/gfs')
    app.register_blueprint(earth_engine_bp, url_prefix='/api/earth-engine')

    # Basic error handler
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'status': 'error', 'message': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
