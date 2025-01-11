# app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from vector_font_search import VectorFontSearch
import os

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Configuration
IMAGES_DIR = "serving_images"  # Directory containing font images
SAVE_DIR = "serving_index"

# Load the saved search engine
search_engine = VectorFontSearch.load(save_dir=SAVE_DIR, images_dir=IMAGES_DIR)


@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/api/search', methods=['POST'])
def search():
    try:
        data = request.json
        query = data.get('query')

        if not query:
            return jsonify({'error': 'No query provided'}), 400

        results = search_engine.search(query, k=12)

        # Modify image paths to use our static route
        for result in results:
            if 'image' in result:
                # Get just the filename from the path
                filename = os.path.basename(result['image'])
                # Replace with URL path
                result['image'] = f'/fonts/{filename}'

        return jsonify(results)

    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500


@app.route('/fonts/<path:filename>')
def serve_font_image(filename):
    """Serve font images from the IMAGES_DIR directory."""
    return send_from_directory(IMAGES_DIR, filename)


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'running',
        'num_fonts': len(search_engine.documents),
        'last_updated': search_engine.metadata.get('last_updated'),
        'model_name': search_engine.metadata.get('model_name')
    })


if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=8080, debug=True)
    app.run(host='0.0.0.0', port=8080)