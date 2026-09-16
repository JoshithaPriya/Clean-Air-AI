import pytest
import requests
import requests_mock
from datetime import datetime, timezone, timedelta
from services.openaq_service import OpenAQClient, OpenAQServiceError

@pytest.fixture
def openaq_client():
    return OpenAQClient()

def get_recent_time_str(hours_ago=0):
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return dt.isoformat().replace('+00:00', 'Z')

def test_fetch_latest_success(openaq_client, requests_mock):
    # Mock data mimicking OpenAQ v3 /locations response with a recent datetimeLast
    recent_time = get_recent_time_str(hours_ago=2)
    mock_locations_response = {
        "meta": {"name": "openaq-api", "limit": 1},
        "results": [
            {
                "id": 123,
                "name": "Test Station",
                "country": {"code": "IN"},
                "provider": {"name": "TestProvider"},
                "coordinates": {"latitude": 28.6, "longitude": 77.2},
                "datetimeLast": {"utc": recent_time, "local": recent_time},
                "sensors": [
                    {
                        "id": 999,
                        "parameter": {"name": "pm25", "units": "µg/m³"}
                    }
                ]
            }
        ]
    }
    
    mock_latest_response = {
        "results": [
            {
                "datetime": {"utc": recent_time, "local": recent_time},
                "value": 45.2,
                "sensorsId": 999,
                "locationsId": 123
            }
        ]
    }
    
    # Check that sort_order=desc is included in the locations request
    requests_mock.get('https://api.openaq.org/v3/locations', json=mock_locations_response)
    requests_mock.get('https://api.openaq.org/v3/locations/123/latest', json=mock_latest_response)
    
    data = openaq_client.fetch_latest_measurements(iso="IN")
    
    # Assert sort_order=desc was requested
    last_request = requests_mock.request_history[0]
    assert 'sort_order=desc' in last_request.query
    
    assert len(data) == 1
    assert data[0]['station_id'] == 123
    assert data[0]['value'] == 45.2
    assert data[0]['timestamp']['utc'] == recent_time

def test_fetch_stale_location_skipped(openaq_client, requests_mock):
    stale_time = get_recent_time_str(hours_ago=72)
    mock_locations_response = {
        "meta": {"name": "openaq-api", "limit": 1},
        "results": [
            {
                "id": 123,
                "datetimeLast": {"utc": stale_time},
                "sensors": [{"id": 999}]
            }
        ]
    }
    
    requests_mock.get('https://api.openaq.org/v3/locations', json=mock_locations_response)
    
    data = openaq_client.fetch_latest_measurements(iso="IN")
    
    # Expect 0 data points because location is stale, and /latest should NOT be called
    assert len(data) == 0
    assert len(requests_mock.request_history) == 1 # Only /locations was called

def test_fetch_missing_datetime_skipped(openaq_client, requests_mock):
    mock_locations_response = {
        "results": [
            {"id": 124, "datetimeLast": None, "sensors": []},
            {"id": 125, "sensors": []} # no datetimeLast key at all
        ]
    }
    requests_mock.get('https://api.openaq.org/v3/locations', json=mock_locations_response)
    
    data = openaq_client.fetch_latest_measurements(iso="IN")
    assert len(data) == 0
    assert len(requests_mock.request_history) == 1

def test_fetch_malformed_datetime_skipped(openaq_client, requests_mock):
    mock_locations_response = {
        "results": [
            {"id": 126, "datetimeLast": {"utc": "not-a-valid-date"}, "sensors": []}
        ]
    }
    requests_mock.get('https://api.openaq.org/v3/locations', json=mock_locations_response)
    
    data = openaq_client.fetch_latest_measurements(iso="IN")
    assert len(data) == 0
    assert len(requests_mock.request_history) == 1

def test_fetch_unauthorized(openaq_client, requests_mock):
    requests_mock.get('https://api.openaq.org/v3/locations', status_code=401)
    
    with pytest.raises(OpenAQServiceError) as exc_info:
        openaq_client.fetch_latest_measurements()
        
    assert exc_info.value.status_code == 401
    assert "Unauthorized" in str(exc_info.value)

def test_fetch_http_error(openaq_client, requests_mock):
    requests_mock.get('https://api.openaq.org/v3/locations', status_code=500)
    
    with pytest.raises(OpenAQServiceError) as exc_info:
        openaq_client.fetch_latest_measurements()
        
    assert exc_info.value.status_code == 500

def test_fetch_timeout(openaq_client, requests_mock):
    requests_mock.get('https://api.openaq.org/v3/locations', exc=requests.exceptions.Timeout)
    
    with pytest.raises(OpenAQServiceError) as exc_info:
        openaq_client.fetch_latest_measurements()
        
    assert exc_info.value.status_code == 504
