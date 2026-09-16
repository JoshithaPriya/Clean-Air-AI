import pytest
import requests
import requests_mock
import os
from unittest.mock import patch
from services.openweathermap_service import OpenWeatherMapClient, OpenWeatherMapServiceError

@pytest.fixture
def owm_client():
    # Make sure we have an API key for the test (so it doesn't fail the 'not self.api_key' check)
    client = OpenWeatherMapClient()
    client.api_key = "test_key"
    return client

def test_fetch_current_weather_success(owm_client, requests_mock):
    mock_response = {
        "coord": {"lon": 80.2707, "lat": 13.0827},
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01n"}],
        "main": {
            "temp": 28.5,
            "feels_like": 32.1,
            "temp_min": 28.5,
            "temp_max": 28.5,
            "pressure": 1008,
            "humidity": 75
        },
        "wind": {"speed": 4.1, "deg": 140},
        "clouds": {"all": 0},
        "dt": 1698240000,
        "sys": {"country": "IN", "sunrise": 1698193853, "sunset": 1698236113},
        "timezone": 19800,
        "id": 1264527,
        "name": "Chennai"
    }
    
    requests_mock.get('https://api.openweathermap.org/data/2.5/weather', json=mock_response)
    
    data = owm_client.fetch_current_weather(lat=13.0827, lon=80.2707)
    
    assert data['location_id'] == 1264527
    assert data['city_name'] == "Chennai"
    assert data['country'] == "IN"
    assert data['coordinates']['latitude'] == 13.0827
    assert data['coordinates']['longitude'] == 80.2707
    assert data['temperature_c'] == 28.5
    assert data['feels_like_c'] == 32.1
    assert data['humidity_percent'] == 75
    assert data['pressure_hpa'] == 1008
    assert data['wind']['speed_m_s'] == 4.1
    assert data['cloud_coverage_percent'] == 0
    assert data['condition'] == "Clear"
    assert data['description'] == "clear sky"
    assert data['precipitation'] is None
    assert data['timestamp_utc'] == "2023-10-25T13:20:00+00:00"

def test_fetch_missing_optional_fields(owm_client, requests_mock):
    # Minimal response
    mock_response = {
        "coord": {"lon": 0, "lat": 0},
        "id": 123,
        "name": "Nowhere"
    }
    
    requests_mock.get('https://api.openweathermap.org/data/2.5/weather', json=mock_response)
    
    data = owm_client.fetch_current_weather(lat=0, lon=0)
    
    assert data['city_name'] == "Nowhere"
    assert data['temperature_c'] is None
    assert data['condition'] == "Unknown"
    assert data['precipitation'] is None

def test_precipitation_parsed(owm_client, requests_mock):
    mock_response = {
        "rain": {"1h": 2.5, "3h": 4.0},
        "snow": {"1h": 1.2}
    }
    
    requests_mock.get('https://api.openweathermap.org/data/2.5/weather', json=mock_response)
    
    data = owm_client.fetch_current_weather(lat=0, lon=0)
    
    assert data['precipitation']['rain_1h'] == 2.5
    assert data['precipitation']['snow_1h'] == 1.2

def test_fetch_unauthorized(owm_client, requests_mock):
    requests_mock.get('https://api.openweathermap.org/data/2.5/weather', status_code=401)
    
    with pytest.raises(OpenWeatherMapServiceError) as exc_info:
        owm_client.fetch_current_weather(lat=0, lon=0)
        
    assert exc_info.value.status_code == 401
    assert "Unauthorized" in str(exc_info.value)

def test_fetch_location_not_found(owm_client, requests_mock):
    requests_mock.get('https://api.openweathermap.org/data/2.5/weather', status_code=404)
    
    with pytest.raises(OpenWeatherMapServiceError) as exc_info:
        owm_client.fetch_current_weather(lat=0, lon=0)
        
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value)

def test_fetch_http_error(owm_client, requests_mock):
    requests_mock.get('https://api.openweathermap.org/data/2.5/weather', status_code=500)
    
    with pytest.raises(OpenWeatherMapServiceError) as exc_info:
        owm_client.fetch_current_weather(lat=0, lon=0)
        
    assert exc_info.value.status_code == 500

def test_fetch_timeout(owm_client, requests_mock):
    requests_mock.get('https://api.openweathermap.org/data/2.5/weather', exc=requests.exceptions.Timeout)
    
    with pytest.raises(OpenWeatherMapServiceError) as exc_info:
        owm_client.fetch_current_weather(lat=0, lon=0)
        
    assert exc_info.value.status_code == 504

@patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": ""})
def test_fetch_missing_api_key():
    client = OpenWeatherMapClient()
    client.api_key = None
    
    with pytest.raises(OpenWeatherMapServiceError) as exc_info:
        client.fetch_current_weather(lat=0, lon=0)
        
    assert exc_info.value.status_code == 401
    assert "Missing" in str(exc_info.value)
