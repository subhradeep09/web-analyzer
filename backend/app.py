import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from website_comparison import compare_websites

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Flask API endpoint ---
@app.route('/compare_websites', methods=['POST'])
def compare_websites_api():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        print(f"Received data: {data}")
        print(f"Received data category: {data.get('category')}")
        websites = data.get('websites', [])
        category = data.get('category', 'ecommerce')

        if not websites:
            return jsonify({"error": "No websites provided"}), 400

        scores = compare_websites(websites, category)
        return jsonify(scores), 200

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Route to serve screenshot files
@app.route('/screenshots/<path:path>')
def serve_screenshots(path):
    return send_from_directory('screenshots', path)

# Run the Flask app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug)
