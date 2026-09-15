# Clean Air & Climate Resilience - Phase 0

## Project Overview
Clean Air & Climate Resilience is a BRICS-ready AI pollution intelligence platform. 

## Phase 0 Scope
This phase establishes the foundational project structure, containing:
- A React frontend.
- A Python Flask backend API.
- Basic frontend-backend communication (CORS enabled).
- Health check API endpoint.
- Environment variables support.

**Note:** Future phases will introduce external APIs (OpenAQ, OpenWeatherMap, etc.), Machine Learning components (Gemini, Vertex AI), databases (BigQuery, Firestore), and cloud deployment infrastructure. These are intentionally omitted in Phase 0.

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
3. Start the React app: `npm start` (App runs at http://localhost:3000)

## API Endpoints
- `GET /api/health` - Returns JSON confirming the backend is operational and running Phase 0.
