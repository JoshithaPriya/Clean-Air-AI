import os
import math
import uuid
import requests
import xarray as xr
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

class GFSServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code

class GFSClient:
    def __init__(self):
        self.base_url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
        self.cache_dir = os.path.join(os.path.dirname(__file__), '..', 'cache', 'gfs')
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_latest_available_cycle(self) -> tuple:
        """
        Walks backward in time to find the most recent GFS cycle published by NOAA.
        GFS runs at 00, 06, 12, 18 UTC and typically takes 3-5 hours to upload.
        """
        now = datetime.now(timezone.utc)
        
        # Start checking from the current hour, stepped back by 6h intervals
        # Actually, let's just step back hour by hour up to 24 hours to find a published run
        for offset_hours in range(4, 48):
            check_time = now - timedelta(hours=offset_hours)
            # Find the nearest past GFS cycle (00, 06, 12, 18)
            cycle_hour = (check_time.hour // 6) * 6
            check_time = check_time.replace(hour=cycle_hour, minute=0, second=0, microsecond=0)
            
            date_str = check_time.strftime("%Y%m%d")
            cycle_str = f"{cycle_hour:02d}"
            
            dir_url = f"{self.base_url}?dir=%2Fgfs.{date_str}%2F{cycle_str}%2Fatmos"
            try:
                resp = requests.get(dir_url, timeout=5)
                if resp.status_code == 200 and f"gfs.t{cycle_str}z.pgrb2.0p25.f000" in resp.text:
                    return date_str, cycle_str
            except requests.RequestException:
                pass
                
        raise GFSServiceError("Could not find a recently published GFS cycle from NOAA NOMADS.", status_code=502)

    def _normalize_longitude(self, lon: float) -> float:
        """Convert -180...180 to 0...360 for NOAA subsetting"""
        return lon if lon >= 0 else lon + 360.0

    def fetch_forecast(self, lat: float, lon: float, forecast_hour: int = 0) -> Dict[str, Any]:
        """
        Downloads a small GFS subset for the requested location and parses it.
        """
        date_str, cycle_str = self._get_latest_available_cycle()
        
        # Create a bounding box of 0.5 degrees around the target
        north = lat + 0.25
        south = lat - 0.25
        
        # NOMADS expects lon in 0-360 format
        center_lon_360 = self._normalize_longitude(lon)
        west = center_lon_360 - 0.25
        east = center_lon_360 + 0.25
        
        fhour_str = f"{forecast_hour:03d}"
        file_name = f"gfs.t{cycle_str}z.pgrb2.0p25.f{fhour_str}"
        
        params = {
            'file': file_name,
            'dir': f"/gfs.{date_str}/{cycle_str}/atmos",
            'subregion': '',
            'leftlon': str(west),
            'rightlon': str(east),
            'toplat': str(north),
            'bottomlat': str(south),
            'var_TMP': 'on',
            'var_DPT': 'on',
            'var_UGRD': 'on',
            'var_VGRD': 'on',
            'var_PRMSL': 'on',
            'var_APCP': 'on',
            'lev_10_m_above_ground': 'on',
            'lev_2_m_above_ground': 'on',
            'lev_mean_sea_level': 'on',
            'lev_surface': 'on'
        }

        # Request data
        try:
            resp = requests.get(self.base_url, params=params, timeout=30)
            if resp.status_code != 200:
                raise GFSServiceError(f"NOAA returned {resp.status_code}: {resp.text[:100]}", status_code=502)
        except requests.RequestException as e:
            raise GFSServiceError(f"NOAA request failed: {str(e)}", status_code=502)

        # Save to cache
        cache_file = os.path.join(self.cache_dir, f"gfs_{lat}_{lon}_{date_str}_{cycle_str}_{fhour_str}_{uuid.uuid4().hex[:8]}.grb2")
        with open(cache_file, 'wb') as f:
            f.write(resp.content)
            
        try:
            return self._parse_grib2(cache_file, lat, center_lon_360, date_str, cycle_str, forecast_hour)
        finally:
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except OSError:
                    pass

    def _parse_grib2(self, file_path: str, target_lat: float, target_lon_360: float, date_str: str, cycle_str: str, forecast_hour: int) -> Dict[str, Any]:
        """
        Parses the GRIB2 file natively using xarray + cfgrib.
        """
        try:
            # cfgrib handles the binary reading natively with xarray
            # We use filter_by_keys to avoid issues with mismatched vertical coordinates (isobaricInhPa vs heightAboveGround)
            # Because we requested exactly what we need, we can load the datasets one by one or all together if they merge cleanly.
            # But usually it's safer to load them by type_of_level.
            
            # Since cfgrib separates variables with different dimensions (e.g. 2m vs 10m vs MSL), we load them independently.
            ds_2m = xr.open_dataset(file_path, engine='cfgrib', backend_kwargs={'filter_by_keys': {'typeOfLevel': 'heightAboveGround', 'level': 2}})
            ds_10m = xr.open_dataset(file_path, engine='cfgrib', backend_kwargs={'filter_by_keys': {'typeOfLevel': 'heightAboveGround', 'level': 10}})
            ds_msl = xr.open_dataset(file_path, engine='cfgrib', backend_kwargs={'filter_by_keys': {'typeOfLevel': 'meanSea'}})
            
            # APCP is surface level
            try:
                ds_sfc = xr.open_dataset(file_path, engine='cfgrib', backend_kwargs={'filter_by_keys': {'typeOfLevel': 'surface'}})
            except Exception:
                ds_sfc = None
            
            # Find nearest grid point
            ds_2m_near = ds_2m.sel(latitude=target_lat, longitude=target_lon_360, method='nearest')
            ds_10m_near = ds_10m.sel(latitude=target_lat, longitude=target_lon_360, method='nearest')
            ds_msl_near = ds_msl.sel(latitude=target_lat, longitude=target_lon_360, method='nearest')
            
            grid_lat = float(ds_2m_near.latitude.values)
            grid_lon = float(ds_2m_near.longitude.values)
            # Revert 360 to standard longitude
            grid_lon_180 = grid_lon if grid_lon <= 180 else grid_lon - 360.0
            target_lon_180 = target_lon_360 if target_lon_360 <= 180 else target_lon_360 - 360.0
            
            # Extract raw values
            t_k = float(ds_2m_near.t2m.values)
            d_k = float(ds_2m_near.d2m.values)
            u = float(ds_10m_near.u10.values)
            v = float(ds_10m_near.v10.values)
            p_pa = float(ds_msl_near.prmsl.values)
            
            apcp_kg_m2 = 0.0
            if ds_sfc and 'tp' in ds_sfc:
                ds_sfc_near = ds_sfc.sel(latitude=target_lat, longitude=target_lon_360, method='nearest')
                apcp_kg_m2 = float(ds_sfc_near.tp.values)
            elif ds_sfc and 'apcp' in ds_sfc:
                # Variable names can fluctuate in xarray parsing depending on cfgrib translation tables
                ds_sfc_near = ds_sfc.sel(latitude=target_lat, longitude=target_lon_360, method='nearest')
                apcp_kg_m2 = float(ds_sfc_near.apcp.values)
                
            # Math and conversions
            temp_c = round(t_k - 273.15, 2)
            dew_c = round(d_k - 273.15, 2)
            pressure_hpa = round(p_pa / 100.0, 1)
            
            # 1 kg/m^2 of water is 1 mm of precipitation
            precip_mm = round(apcp_kg_m2, 2)
            
            wind_speed = round(math.sqrt(u**2 + v**2), 2)
            # Meteorological wind direction
            wind_dir = round((180 + (180 / math.pi) * math.atan2(u, v)) % 360, 1)
            
            # Time calculations
            cycle_time = datetime(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]), int(cycle_str), tzinfo=timezone.utc)
            forecast_time = cycle_time + timedelta(hours=forecast_hour)
            
            ds_2m.close()
            ds_10m.close()
            ds_msl.close()
            if ds_sfc:
                ds_sfc.close()
                
            return {
                "source": "NOAA_GFS",
                "model": "GFS 0.25 degree",
                "cycle": cycle_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "forecast_time": forecast_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "forecast_hour": forecast_hour,
                "location": {
                    "requested_latitude": target_lat,
                    "requested_longitude": target_lon_180,
                    "grid_latitude": round(grid_lat, 2),
                    "grid_longitude": round(grid_lon_180, 2)
                },
                "weather": {
                    "temperature_2m": temp_c,
                    "dewpoint_temperature_2m": dew_c,
                    "surface_pressure": pressure_hpa,
                    "u_wind_10m": round(u, 2),
                    "v_wind_10m": round(v, 2),
                    "wind_speed": wind_speed,
                    "wind_direction": wind_dir,
                    "precipitation": precip_mm
                }
            }
        except Exception as e:
            raise GFSServiceError(f"Failed to parse GFS GRIB2 data: {str(e)}", status_code=500)
