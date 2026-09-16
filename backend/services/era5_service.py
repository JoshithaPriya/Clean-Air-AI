import os
import math
import uuid
from typing import Dict, Any, List
import cdsapi
import netCDF4
import numpy as np
from datetime import datetime

class ERA5ServiceError(Exception):
    """Custom exception for ERA5 service errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code

class ERA5Client:
    def __init__(self):
        self.cds_url = os.environ.get('CDS_URL', 'https://cds.climate.copernicus.eu/api')
        # The user specifically mentioned adding "ERA5_API_KEY", so we check both
        self.api_key = os.environ.get('CDS_API_KEY') or os.environ.get('ERA5_API_KEY')
        self.cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache', 'era5')
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # We only initialize the client lazily to avoid exceptions during app startup if key is missing
        self._client = None

    def _get_client(self):
        if not self.api_key:
            raise ERA5ServiceError("Unauthorized: Missing CDS API Key in configuration", status_code=401)
        
        if not self._client:
            # We can pass url and key directly to bypass ~/.cdsapirc file requirement
            self._client = cdsapi.Client(url=self.cds_url, key=self.api_key, quiet=True)
        return self._client

    def fetch_historical_weather(self, lat: float, lon: float, date_str: str, time_str: str = None) -> List[Dict[str, Any]]:
        """
        Fetches historical ERA5 weather for a given latitude, longitude, and date.
        Returns normalized list of hourly data.
        """
        client = self._get_client()
        
        # Parse date
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ERA5ServiceError("Invalid date format. Expected YYYY-MM-DD", status_code=400)
            
        # Define the subset variables
        variables = [
            '10m_u_component_of_wind', 
            '10m_v_component_of_wind', 
            '2m_dewpoint_temperature',
            '2m_temperature', 
            'surface_pressure', 
            'total_precipitation'
        ]
        
        # Determine time scope (limit to 1-4 hours if time_str specified, otherwise all 24h or a subset for safety in Phase 1C)
        # To avoid massive downloads during Phase 1C, we'll download just 4 hours by default unless time_str is given.
        if time_str:
            times = [time_str]
        else:
            times = ['00:00', '06:00', '12:00', '18:00']

        # Bounding box: ERA5 is ~30km grid (0.25 degrees). 
        # We create a tight bounding box around the point: [North, West, South, East]
        north = lat + 0.125
        south = lat - 0.125
        west = lon - 0.125
        east = lon + 0.125
        
        file_name = f"era5_{lat}_{lon}_{date_str}_{uuid.uuid4().hex[:8]}.nc"
        file_path = os.path.join(self.cache_dir, file_name)

        request_payload = {
            'product_type': 'reanalysis',
            'variable': variables,
            'year': str(date_obj.year),
            'month': f"{date_obj.month:02d}",
            'day': f"{date_obj.day:02d}",
            'time': times,
            'area': [north, west, south, east],
            'data_format': 'netcdf',
            'download_format': 'unarchived',
        }

        try:
            # Download the data
            client.retrieve('reanalysis-era5-single-levels', request_payload, file_path)
            
            # Parse and normalize
            results = self._parse_netcdf(file_path, lat, lon)
            return results
            
        except Exception as e:
            # Handle CDS exceptions carefully to not leak keys
            error_msg = str(e)
            if self.api_key and self.api_key in error_msg:
                error_msg = error_msg.replace(self.api_key, "HIDDEN_KEY")
            raise ERA5ServiceError(f"Failed to fetch ERA5 data: {error_msg}", status_code=502)
        finally:
            # Cleanup the cached file to save space
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass

    def _parse_netcdf(self, file_path: str, target_lat: float, target_lon: float) -> List[Dict[str, Any]]:
        """
        Reads the NetCDF file(s) and normalizes the grid values closest to the target coordinates.
        Handles both single .nc files and .zip files containing multiple .nc files (CDS API behavior).
        """
        import zipfile
        import glob
        import shutil

        extract_dir = None
        nc_files = [file_path]

        if zipfile.is_zipfile(file_path):
            extract_dir = file_path + "_unzipped"
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            nc_files = glob.glob(f"{extract_dir}/*.nc")

        # Dictionary to accumulate variables per timestamp
        # Key: timestamp string, Value: Dict of parsed data
        merged_results = {}

        try:
            for nc_file in nc_files:
                dataset = netCDF4.Dataset(nc_file, 'r')
                
                # Use 'valid_time' if available (new CDS), otherwise 'time'
                time_var_name = 'valid_time' if 'valid_time' in dataset.variables else 'time'
                
                lats = dataset.variables['latitude'][:]
                lons = dataset.variables['longitude'][:]
                times = dataset.variables[time_var_name]
                
                lat_idx = (np.abs(lats - target_lat)).argmin()
                lon_idx = (np.abs(lons - target_lon)).argmin()
                
                actual_lat = float(lats[lat_idx])
                actual_lon = float(lons[lon_idx])
                
                time_dates = netCDF4.num2date(times[:], times.units)
                
                for t_idx, t_date in enumerate(time_dates):
                    # Format timestamp safely (ISO 8601 UTC)
                    timestamp_str = t_date.isoformat()
                    if not timestamp_str.endswith('Z') and not '+' in timestamp_str:
                        timestamp_str += 'Z'
                        
                    if timestamp_str not in merged_results:
                        merged_results[timestamp_str] = {
                            "source": "ERA5",
                            "timestamp": timestamp_str,
                            "location": {
                                "latitude": actual_lat,
                                "longitude": actual_lon,
                                "requested_latitude": target_lat,
                                "requested_longitude": target_lon
                            },
                            "u_wind_10m": 0.0,
                            "v_wind_10m": 0.0,
                            "wind_speed": 0.0,
                            "wind_direction": 0.0,
                            "temperature_2m": 0.0,
                            "dewpoint_temperature_2m": 0.0,
                            "surface_pressure": 0.0,
                            "total_precipitation": 0.0
                        }
                    
                    res = merged_results[timestamp_str]
                    
                    if 'u10' in dataset.variables:
                        res['u_wind_10m'] = round(float(dataset.variables['u10'][t_idx, lat_idx, lon_idx]), 2)
                    if 'v10' in dataset.variables:
                        res['v_wind_10m'] = round(float(dataset.variables['v10'][t_idx, lat_idx, lon_idx]), 2)
                    if 't2m' in dataset.variables:
                        res['temperature_2m'] = round(float(dataset.variables['t2m'][t_idx, lat_idx, lon_idx]) - 273.15, 2)
                    if 'd2m' in dataset.variables:
                        res['dewpoint_temperature_2m'] = round(float(dataset.variables['d2m'][t_idx, lat_idx, lon_idx]) - 273.15, 2)
                    if 'sp' in dataset.variables:
                        res['surface_pressure'] = round(float(dataset.variables['sp'][t_idx, lat_idx, lon_idx]) / 100.0, 1)
                    if 'tp' in dataset.variables:
                        val = dataset.variables['tp'][t_idx, lat_idx, lon_idx]
                        if not np.ma.is_masked(val):
                            res['total_precipitation'] = round(float(val) * 1000.0, 4)
                            
                    # Recompute wind math safely if u and v are present
                    if 'u10' in dataset.variables and 'v10' in dataset.variables:
                        u = res['u_wind_10m']
                        v = res['v_wind_10m']
                        res['wind_speed'] = round(math.sqrt(u**2 + v**2), 2)
                        res['wind_direction'] = round((180 + (180 / math.pi) * math.atan2(u, v)) % 360, 1)

                dataset.close()
                
            return sorted(list(merged_results.values()), key=lambda x: x['timestamp'])
            
        except Exception as e:
            raise ERA5ServiceError(f"Failed to parse NetCDF data: {str(e)}", status_code=500)
        finally:
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
