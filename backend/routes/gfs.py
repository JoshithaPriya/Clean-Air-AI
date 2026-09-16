from flask import Blueprint, request, jsonify
from services.gfs_service import GFSClient, GFSServiceError

gfs_bp = Blueprint('gfs', __name__)
gfs_client = GFSClient()

@gfs_bp.route('/gfs', methods=['GET'])
def get_gfs_data():
    """
    Retrieves numerical weather forecast from NOAA GFS for a given location.
    Required query parameters:
    - lat: Latitude (-90 to 90)
    - lon: Longitude (-180 to 180)
    Optional:
    - forecast_hour: Forecast hour offset (default: 0). Valid multiples of 3.
    """
    lat_str = request.args.get('lat')
    lon_str = request.args.get('lon')
    fhour_str = request.args.get('forecast_hour', '0')
    
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
        
    try:
        fhour = int(fhour_str)
    except ValueError:
        return jsonify({
            'status': 'error', 
            'message': "Invalid 'forecast_hour'. Must be an integer."
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
        
    if fhour < 0 or fhour > 384:
        return jsonify({
            'status': 'error', 
            'message': "Forecast hour must be between 0 and 384."
        }), 400
        
    if fhour % 3 != 0:
        # NOAA GFS provides hourly up to 120, then 3-hourly. We restrict to 3-hourly for simplicity.
        return jsonify({
            'status': 'error', 
            'message': "Forecast hour must be a multiple of 3 (e.g., 0, 3, 6, 9, 12)."
        }), 400

    try:
        data = gfs_client.fetch_forecast(lat=lat, lon=lon, forecast_hour=fhour)
        return jsonify({
            'status': 'success',
            'data': data
        }), 200
        
    except GFSServiceError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), e.status_code
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'An unexpected error occurred processing the GFS request.'
        }), 500
