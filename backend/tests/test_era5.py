import pytest
from unittest.mock import patch, MagicMock
from services.era5_service import ERA5Client, ERA5ServiceError

@pytest.fixture
def era5_client():
    client = ERA5Client()
    client.api_key = "test_key"
    return client

@patch('services.era5_service.ERA5Client._get_client')
@patch('services.era5_service.ERA5Client._parse_netcdf')
def test_fetch_historical_success(mock_parse, mock_get_client, era5_client):
    mock_cds = MagicMock()
    mock_get_client.return_value = mock_cds
    
    # Mock parse to return dummy data
    mock_parse.return_value = [{
        "source": "ERA5",
        "temperature_2m": 25.0
    }]
    
    data = era5_client.fetch_historical_weather(lat=13.0, lon=80.0, date_str="2026-09-15", time_str="12:00")
    
    assert len(data) == 1
    assert data[0]['temperature_2m'] == 25.0
    
    # Verify the client was called properly
    mock_cds.retrieve.assert_called_once()
    args, kwargs = mock_cds.retrieve.call_args
    assert args[0] == 'reanalysis-era5-single-levels'
    assert args[1]['year'] == '2026'
    assert args[1]['month'] == '09'
    assert args[1]['time'] == ['12:00']

@patch('services.era5_service.ERA5Client._get_client')
def test_fetch_historical_invalid_date(mock_get_client, era5_client):
    with pytest.raises(ERA5ServiceError) as exc:
        era5_client.fetch_historical_weather(lat=0, lon=0, date_str="bad-date")
    assert exc.value.status_code == 400

@patch('services.era5_service.ERA5Client._get_client')
def test_fetch_historical_api_error(mock_get_client, era5_client):
    mock_cds = MagicMock()
    mock_cds.retrieve.side_effect = Exception("CDS API is down, api_key: test_key")
    mock_get_client.return_value = mock_cds
    
    with pytest.raises(ERA5ServiceError) as exc:
        era5_client.fetch_historical_weather(lat=0, lon=0, date_str="2026-09-15")
        
    assert exc.value.status_code == 502
    assert "test_key" not in str(exc.value) # Ensure key is hidden!
    assert "HIDDEN_KEY" in str(exc.value)

def test_missing_api_key():
    client = ERA5Client()
    client.api_key = None
    with pytest.raises(ERA5ServiceError) as exc:
        client._get_client()
    assert exc.value.status_code == 401

@patch('netCDF4.Dataset')
@patch('netCDF4.num2date')
def test_parse_netcdf_math(mock_num2date, mock_dataset):
    # This tests the math without hitting the network or needing a real .nc file
    from datetime import datetime
    import numpy as np
    
    client = ERA5Client()
    
    # Setup mocks
    mock_ds = MagicMock()
    mock_dataset.return_value = mock_ds
    mock_num2date.return_value = [datetime(2026, 9, 15, 12, 0)]
    
    # Create simple 1x1 grid arrays
    mock_ds.variables = {
        'latitude': np.array([13.0]),
        'longitude': np.array([80.0]),
        'time': MagicMock(units='hours since 1900-01-01'),
        # u=3, v=4 -> wind speed = 5
        'u10': np.array([[[3.0]]]), 
        'v10': np.array([[[4.0]]]),
        # 300K = ~26.85C
        't2m': np.array([[[300.15]]]),
        'd2m': np.array([[[290.15]]]),
        # 101300 Pa = 1013.0 hPa
        'sp': np.array([[[101300.0]]]),
        # 0.005 m = 5 mm
        'tp': np.array([[[0.005]]])
    }
    
    results = client._parse_netcdf('dummy.nc', 13.0, 80.0)
    
    assert len(results) == 1
    res = results[0]
    
    assert res['temperature_2m'] == 27.0
    assert res['surface_pressure'] == 1013.0
    assert res['wind_speed'] == 5.0
    assert res['total_precipitation'] == 5.0
    
    # wind dir math: u=3, v=4. Wind blows *towards* NE, so it comes from SW.
    # atan2(3, 4) = ~36.8 degrees (heading). 
    # Meteorological direction (from): 180 + 36.8 = 216.9
    assert abs(res['wind_direction'] - 216.9) < 1.0
