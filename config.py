import os

# Google Maps API key (required for route generation)
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("MAPS_API_KEY", "")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))
DEBUG = os.getenv("DEBUG", "false").strip().lower() == "true"

# Simulation parameters
TIME_STEP_SECONDS = int(os.getenv("TIME_STEP_SECONDS", "60"))
CHARGE_THRESHOLD = float(os.getenv("CHARGE_THRESHOLD", "0.2"))
OPTIMIZATION_INTERVAL = int(os.getenv("OPTIMIZATION_INTERVAL", "10"))
