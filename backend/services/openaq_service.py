import os
import requests
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

class OpenAQServiceError(Exception):
    """Custom exception for OpenAQ service errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


class OpenAQClient:
    def __init__(self):
        self.base_url = os.environ.get('OPENAQ_BASE_URL', 'https://api.openaq.org/v3')
        self.api_key = os.environ.get('OPENAQ_API_KEY')
        self.timeout = 10 
        
        try:
            self.freshness_hours = int(os.environ.get('OPENAQ_FRESHNESS_HOURS', 48))
        except ValueError:
            self.freshness_hours = 48

    def _get_headers(self) -> Dict[str, str]:
        headers = {'Accept': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def fetch_latest_measurements(self, iso: str = None, coordinates: str = None, radius: int = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches latest air quality measurements from OpenAQ v3 and normalizes the response.
        Since v3 separates locations and measurements, this performs a locations fetch first,
        followed by a latest fetch for each location.
        """
        locations_endpoint = f"{self.base_url}/locations"
        params = {
            'limit': limit,
            'sort_order': 'desc'
        }
        
        if iso:
            params['iso'] = iso
        if coordinates:
            params['coordinates'] = coordinates
        if radius:
            params['radius'] = radius

        try:
            # 1. Fetch Locations
            res = requests.get(
                locations_endpoint, 
                params=params, 
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if res.status_code == 401:
                raise OpenAQServiceError("Unauthorized: Invalid or missing OpenAQ API Key", status_code=401)
            if res.status_code != 200:
                raise OpenAQServiceError(f"OpenAQ API returned status {res.status_code} for locations", status_code=res.status_code)
                
            locations_data = res.json()
            if 'results' not in locations_data:
                raise OpenAQServiceError("Unexpected OpenAQ response format (missing 'results')", status_code=502)
                
            raw_locations = locations_data['results']
            normalized_results = []
            
            # Helper for freshness check
            now_utc = datetime.now(timezone.utc)
            threshold = timedelta(hours=self.freshness_hours)
            
            # 2. For each location, fetch its latest measurements
            for loc in raw_locations:
                loc_id = loc.get('id')
                if not loc_id:
                    continue
                    
                # 3. Check freshness
                datetime_last = loc.get('datetimeLast')
                if not datetime_last or not isinstance(datetime_last, dict):
                    continue
                    
                utc_str = datetime_last.get('utc')
                if not utc_str:
                    continue
                    
                try:
                    # OpenAQ format: "2026-09-15T15:00:00Z"
                    utc_str = utc_str.replace('Z', '+00:00')
                    loc_time = datetime.fromisoformat(utc_str)
                    
                    if now_utc - loc_time > threshold:
                        continue # Stale location, skip it
                except ValueError:
                    # Malformed date, skip safely
                    continue
                    
                # Create a map of sensor ID to parameter info for this location
                sensors = loc.get('sensors', [])
                sensor_map = {}
                for s in sensors:
                    sensor_id = s.get('id')
                    param = s.get('parameter', {})
                    if sensor_id:
                        sensor_map[sensor_id] = param
                
                latest_endpoint = f"{self.base_url}/locations/{loc_id}/latest"
                latest_res = requests.get(
                    latest_endpoint, 
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                if latest_res.status_code == 200:
                    latest_data = latest_res.json().get('results', [])
                    for measurement in latest_data:
                        sensor_id = measurement.get('sensorsId')
                        param_info = sensor_map.get(sensor_id, {})
                        
                        provider = loc.get('provider', {})
                        country = loc.get('country', {})
                        coords = loc.get('coordinates', {})
                        
                        normalized_results.append({
                            'station_id': loc_id,
                            'name': loc.get('name'),
                            'country': country.get('code') if isinstance(country, dict) else country,
                            'coordinates': {
                                'latitude': coords.get('latitude') if coords else None,
                                'longitude': coords.get('longitude') if coords else None
                            },
                            'sensor_id': sensor_id,
                            'timestamp': {
                                'utc': measurement.get('datetime', {}).get('utc'),
                                'local': measurement.get('datetime', {}).get('local')
                            },
                            'pollutant': param_info.get('name', 'unknown'),
                            'value': measurement.get('value'),
                            'unit': param_info.get('units'),
                            'source': provider.get('name')
                        })
                        
            return normalized_results
            
        except requests.exceptions.Timeout:
            raise OpenAQServiceError("Request to OpenAQ timed out", status_code=504)
        except requests.exceptions.RequestException as e:
            raise OpenAQServiceError(f"Failed to communicate with OpenAQ: {str(e)}", status_code=502)
        except ValueError:
            raise OpenAQServiceError("Failed to parse JSON response from OpenAQ", status_code=502)
