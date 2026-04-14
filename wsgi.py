"""
Entry point for running the Flask application.
"""

from app.app import FlaskApp

# Initialize the Flask application
app = FlaskApp()

if __name__ == "__main__":
    # Run the application on all available IPs with debugging enabled
    app.run(debug=True, use_reloader=False)