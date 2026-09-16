# Clean Air & Climate Resilience - Phase 0

## Project Overview
Clean Air & Climate Resilience is a BRICS-ready AI pollution intelligence platform. 

## Phase 1B Scope (Current)
This phase introduces the **OpenWeatherMap Live Weather Connector**.
It includes:
- A dedicated OpenWeatherMap client service to fetch current weather.
- Normalization of raw weather responses into a standard internal format.
- A new modular `weather` blueprint route (`/api/weather/openweathermap`).
- Expanded unit testing with `pytest` for the new connector.

## Phase 1A Scope
This phase introduced the **OpenAQ Data Connector**.

## Phase 0 Scope
This phase established the foundational project structure, containing:

## Technology Stack
- **Frontend**: React
- **Backend**: Python 3.x, Flask, flask-cors, python-dotenv
- **Development**: Local virtual environment, Google Antigravity

## Project Structure
```text
/
├── backend/
│   ├── venv/            # Python virtual environment (ignored in git)
│   ├── app.py           # Main Flask application
│   ├── requirements.txt # Python dependencies
│   ├── .env             # Local environment variables
│   └── .env.example     # Example environment variables
├── frontend/
│   ├── public/          # Static assets
│   ├── src/             # React source code
│   └── package.json     # Node dependencies
├── .gitignore           # Ignored files and folders
└── README.md            # Project documentation
```

## Prerequisites
- Python 3.x
- Node.js & npm

## Setup & Running Locally

### Backend Setup
1. Navigate to the backend directory: `cd backend`
2. Create virtual environment: `python -m venv venv`
3. Activate virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Unix/macOS: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Run the server: `python app.py` (Server starts at http://localhost:5000)

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Start the React app: `npm run dev` (App runs at http://localhost:3000)

### Testing
1. Navigate to the backend directory: `cd backend`
2. Ensure virtual environment is activated.
3. Run the test suite: `pytest tests/`

## API Endpoints
- `GET /api/health` - Returns JSON confirming the backend is operational.
- `GET /api/air-quality/openaq?iso={CountryCode}&limit={Limit}` - Returns normalized OpenAQ air quality measurements.
- `GET /api/weather/openweathermap?lat={Latitude}&lon={Longitude}` - Returns normalized current weather data.
  - **Example Response:**
    ```json
    {
      "status": "success",
      "data": {
        "location_id": 1264527,
        "city_name": "Chennai",
        "country": "IN",
        "coordinates": {
          "latitude": 13.0827,
          "longitude": 80.2707
        },
        "timestamp_utc": "2023-10-25T13:20:00+00:00",
        "temperature_c": 28.5,
        "feels_like_c": 32.1,
        "humidity_percent": 75,
        "pressure_hpa": 1008,
        "wind": {
          "speed_m_s": 4.1,
          "direction_deg": 140
        },
        "cloud_coverage_percent": 0,
        "condition": "Clear",
        "description": "clear sky",
        "precipitation": null,
        "timezone_offset_seconds": 19800
      }
    }
    ```
