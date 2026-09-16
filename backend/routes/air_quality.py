from flask import Blueprint, request, jsonify
from services.openaq_service import OpenAQClient, OpenAQServiceError

air_quality_bp = Blueprint('air_quality', __name__)
openaq_client = OpenAQClient()

@air_quality_bp.route('/openaq', methods=['GET'])
def get_openaq_data():
    """
    Retrieves air quality data from OpenAQ v3 and returns it in a normalized format.
    Query parameters:
    - iso: Filter by country ISO code (e.g. 'IN', 'US')
    - coordinates: Filter by center coordinates 'lat,lng'
    - radius: Search radius in meters (default to 1000 if coordinates provided)
    - limit: Limit the number of locations to retrieve (default: 5)
    """
    iso = request.args.get('iso')
    coordinates = request.args.get('coordinates')
    
    try:
        limit = int(request.args.get('limit', 5))
        radius = request.args.get('radius')
        if radius:
            radius = int(radius)
    except ValueError:
        return jsonify({
            'status': 'error', 
            'message': "Invalid 'limit' or 'radius' parameter. Must be an integer."
        }), 400

    try:
        data = openaq_client.fetch_latest_measurements(
            iso=iso, 
            coordinates=coordinates, 
            radius=radius, 
            limit=limit
        )
        return jsonify({
            'status': 'success',
            'data': data
        }), 200
        
    except OpenAQServiceError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), e.status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred processing the OpenAQ request.'
        }), 500
