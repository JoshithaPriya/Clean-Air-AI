from flask import Blueprint, request, jsonify
from services.openweathermap_service import OpenWeatherMapClient, OpenWeatherMapServiceError

weather_bp = Blueprint('weather', __name__)
owm_client = OpenWeatherMapClient()

@weather_bp.route('/openweathermap', methods=['GET'])
def get_openweathermap_data():
    """
    Retrieves current weather data from OpenWeatherMap and returns it in a normalized format.
    Required query parameters:
    - lat: Latitude (-90 to 90)
    - lon: Longitude (-180 to 180)
    """
    lat_str = request.args.get('lat')
    lon_str = request.args.get('lon')
    
    if not lat_str or not lon_str:
        return jsonify({
            'status': 'error', 
            'message': "Missing required query parameters: 'lat' and 'lon'."
        }), 400
        
    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        return jsonify({
            'status': 'error', 
            'message': "Invalid 'lat' or 'lon' parameter. Must be numeric."
        }), 400
        
    if not (-90 <= lat <= 90):
        return jsonify({
            'status': 'error', 
            'message': "Latitude must be between -90 and 90."
        }), 400
        
    if not (-180 <= lon <= 180):
        return jsonify({
            'status': 'error', 
            'message': "Longitude must be between -180 and 180."
        }), 400

    try:
        data = owm_client.fetch_current_weather(lat=lat, lon=lon)
        return jsonify({
            'status': 'success',
            'data': data
        }), 200
        
    except OpenWeatherMapServiceError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), e.status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred processing the OpenWeatherMap request.'
        }), 500
