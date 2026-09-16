from flask import Blueprint, request, jsonify
from services.era5_service import ERA5Client, ERA5ServiceError

era5_bp = Blueprint('era5', __name__)
era5_client = ERA5Client()

@era5_bp.route('/era5', methods=['GET'])
def get_era5_data():
    """
    Retrieves historical ERA5 weather data for a specified date and location.
    Required query parameters:
    - lat: Latitude (-90 to 90)
    - lon: Longitude (-180 to 180)
    - date: YYYY-MM-DD
    Optional:
    - time: HH:MM
    """
    lat_str = request.args.get('lat')
    lon_str = request.args.get('lon')
    date_str = request.args.get('date')
    time_str = request.args.get('time')
    
    if not lat_str or not lon_str or not date_str:
        return jsonify({
            'status': 'error', 
            'message': "Missing required query parameters: 'lat', 'lon', and 'date'."
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
        data = era5_client.fetch_historical_weather(lat=lat, lon=lon, date_str=date_str, time_str=time_str)
        return jsonify({
            'status': 'success',
            'data': data
        }), 200
        
    except ERA5ServiceError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), e.status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred processing the ERA5 request.'
        }), 500
