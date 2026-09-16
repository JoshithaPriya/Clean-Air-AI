import pytest
import math
from unittest.mock import patch, MagicMock
from services.gfs_service import GFSClient, GFSServiceError

@pytest.fixture
def gfs_client():
    return GFSClient()

@patch('requests.head')
def test_get_latest_available_cycle_success(mock_head, gfs_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_head.return_value = mock_resp
    
    date_str, cycle_str = gfs_client._get_latest_available_cycle()
    
    # We just ensure it returns strings
    assert isinstance(date_str, str)
    assert len(date_str) == 8
    assert isinstance(cycle_str, str)
    assert len(cycle_str) == 2

@patch('requests.head')
def test_get_latest_available_cycle_fail(mock_head, gfs_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_head.return_value = mock_resp
    
    with pytest.raises(GFSServiceError) as exc:
        gfs_client._get_latest_available_cycle()
        
    assert exc.value.status_code == 502
    assert "Could not find" in str(exc.value)

def test_normalize_longitude(gfs_client):
    assert gfs_client._normalize_longitude(80.27) == 80.27
    assert gfs_client._normalize_longitude(-80.27) == 279.73

@patch('services.gfs_service.GFSClient._get_latest_available_cycle')
@patch('requests.get')
@patch('services.gfs_service.GFSClient._parse_grib2')
def test_fetch_forecast_success(mock_parse, mock_get, mock_cycle, gfs_client):
    mock_cycle.return_value = ("20260915", "12")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"fake_grib_data"
    mock_get.return_value = mock_resp
    
    mock_parse.return_value = {"temperature_2m": 25.0}
    
    res = gfs_client.fetch_forecast(lat=13.0, lon=-80.0, forecast_hour=6)
    
    assert res["temperature_2m"] == 25.0
    mock_parse.assert_called_once()
    
    # Check bounding box params
    args, kwargs = mock_get.call_args
    params = kwargs['params']
    assert params['leftlon'] == '279.75' # -80 -> 280, 280 - 0.25 = 279.75
    assert params['rightlon'] == '280.25'
    assert params['toplat'] == '13.25'
    assert params['bottomlat'] == '12.75'

@patch('xarray.open_dataset')
def test_parse_grib2_math(mock_xr_open, gfs_client):
    # Mock xarray datasets
    ds_2m = MagicMock()
    ds_10m = MagicMock()
    ds_msl = MagicMock()
    ds_sfc = MagicMock()
    
    # Setup sel() methods
    mock_near = MagicMock()
    ds_2m.sel.return_value = mock_near
    ds_10m.sel.return_value = mock_near
    ds_msl.sel.return_value = mock_near
    ds_sfc.sel.return_value = mock_near
    
    # Setup scalar values
    mock_near.latitude.values = 13.0
    mock_near.longitude.values = 280.0
    mock_near.t2m.values = 300.15 # 27.0 C
    mock_near.d2m.values = 290.15 # 17.0 C
    mock_near.u10.values = -3.0
    mock_near.v10.values = -4.0 # Wind speed = 5.0
    mock_near.prmsl.values = 101300.0 # 1013.0 hPa
    mock_near.apcp.values = 5.5 # 5.5 mm
    
    # Custom contains so 'tp' is False, 'apcp' is True
    ds_sfc.__contains__.side_effect = lambda key: key == 'apcp'
    
    mock_xr_open.side_effect = [ds_2m, ds_10m, ds_msl, ds_sfc]
    
    res = gfs_client._parse_grib2("dummy.grb2", 13.0, 280.0, "20260915", "12", 6)
    
    assert res['location']['grid_longitude'] == -80.0
    w = res['weather']
    assert w['temperature_2m'] == 27.0
    assert w['dewpoint_temperature_2m'] == 17.0
    assert w['surface_pressure'] == 1013.0
    assert w['wind_speed'] == 5.0
    assert w['precipitation'] == 5.5
    
    # Wind direction math
    u = -3.0
    v = -4.0
    expected_dir = (180 + (180 / math.pi) * math.atan2(u, v)) % 360
    assert w['wind_direction'] == round(expected_dir, 1)
