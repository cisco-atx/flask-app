"""WSGI entry point for the Flask application.

This module initializes and exposes the Flask application instance
for use by WSGI servers. It also allows running the app directly
for development purposes.

File path: wsgi.py
"""
from app.app import FlaskApp

# Initialize the Flask application
app = FlaskApp()

if __name__ == "__main__":
    """Run the Flask development server."""
    # Run the application on all available IPs with debugging enabled
    app.run(debug=True, use_reloader=False)
