import os
import requests
from typing import Dict, Any
from datetime import datetime, timezone

class OpenWeatherMapServiceError(Exception):
    """Custom exception for OpenWeatherMap service errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class OpenWeatherMapClient:
    def __init__(self):
        self.base_url = os.environ.get('OPENWEATHERMAP_BASE_URL', 'https://api.openweathermap.org/data/2.5/weather')
        self.api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        self.timeout = 10 

    def fetch_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Fetches current weather from OpenWeatherMap and normalizes the response.
        """
        self.api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        if not self.api_key:
            raise OpenWeatherMapServiceError("Unauthorized: Missing OpenWeatherMap API Key in configuration", status_code=401)
            
        params = {
            'lat': lat,
            'lon': lon,
            'appid': self.api_key,
            'units': 'metric' # Standardize on metric (Celsius, m/s)
        }

        try:
            res = requests.get(
                self.base_url, 
                params=params, 
                timeout=self.timeout
            )
            
            if res.status_code == 401:
                raise OpenWeatherMapServiceError("Unauthorized: Invalid OpenWeatherMap API Key", status_code=401)
            if res.status_code == 404:
                raise OpenWeatherMapServiceError("Location not found on OpenWeatherMap", status_code=404)
            if res.status_code != 200:
                raise OpenWeatherMapServiceError(f"OpenWeatherMap API returned status {res.status_code}", status_code=res.status_code)
                
            data = res.json()
            return self._normalize_data(data)
            
        except requests.exceptions.Timeout:
            raise OpenWeatherMapServiceError("Request to OpenWeatherMap timed out", status_code=504)
        except requests.exceptions.RequestException as e:
            raise OpenWeatherMapServiceError(f"Failed to communicate with OpenWeatherMap: {str(e)}", status_code=502)
        except ValueError:
            raise OpenWeatherMapServiceError("Failed to parse JSON response from OpenWeatherMap", status_code=502)

    def _normalize_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforms OpenWeatherMap raw response into our internal normalized schema.
        Extracts only the required fields safely.
        """
        coords = raw_data.get('coord', {})
        main = raw_data.get('main', {})
        wind = raw_data.get('wind', {})
        clouds = raw_data.get('clouds', {})
        weather_array = raw_data.get('weather', [])
        sys = raw_data.get('sys', {})
        
        weather_condition = "Unknown"
        weather_description = "Unknown"
        if weather_array and isinstance(weather_array, list) and len(weather_array) > 0:
            weather_condition = weather_array[0].get('main', 'Unknown')
            weather_description = weather_array[0].get('description', 'Unknown')
            
        # Parse timestamp safely
        dt = raw_data.get('dt')
        timestamp_utc = None
        if dt:
            try:
                timestamp_utc = datetime.fromtimestamp(dt, tz=timezone.utc).isoformat()
            except (ValueError, TypeError, OSError):
                pass
                
        # Parse precipitation if available (usually 1h or 3h volume)
        precipitation = {}
        rain = raw_data.get('rain', {})
        snow = raw_data.get('snow', {})
        if rain:
            precipitation['rain_1h'] = rain.get('1h')
            precipitation['rain_3h'] = rain.get('3h')
        if snow:
            precipitation['snow_1h'] = snow.get('1h')
            precipitation['snow_3h'] = snow.get('3h')
            
        return {
            'location_id': raw_data.get('id'),
            'city_name': raw_data.get('name'),
            'country': sys.get('country'),
            'coordinates': {
                'latitude': coords.get('lat'),
                'longitude': coords.get('lon')
            },
            'timestamp_utc': timestamp_utc,
            'temperature_c': main.get('temp'),
            'feels_like_c': main.get('feels_like'),
            'humidity_percent': main.get('humidity'),
            'pressure_hpa': main.get('pressure'),
            'wind': {
                'speed_m_s': wind.get('speed'),
                'direction_deg': wind.get('deg')
            },
            'cloud_coverage_percent': clouds.get('all'),
            'condition': weather_condition,
            'description': weather_description,
            'precipitation': precipitation if precipitation else None,
            'timezone_offset_seconds': raw_data.get('timezone')
        }
