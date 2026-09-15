import os
from flask import Flask, jsonify
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    
    # Enable CORS for local development. In production, this should be restricted.
    CORS(app)
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'success',
            'message': 'Backend is running!',
            'phase': 'Phase 0'
        }), 200

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
