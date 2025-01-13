from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ingredient_api import load_database, merge_ewg_data
from ml_classifier import IngredientMLClassifier
import os
from PIL import Image
import pytesseract
import io

app = Flask(__name__, static_folder='../frontend')
CORS(app)

# Load database
print("Loading database from:", os.path.join(os.path.dirname(__file__), 'toxic_chemicals_database.json'))
harmful_ingredients, safe_alternatives, toxicity_categories = load_database()

# Initialize ML classifier
ml_classifier = IngredientMLClassifier()
print("Training ML model...")
if not ml_classifier.train():
    print("Failed to train ML model")

# Start periodic database update
print("Starting periodic database update...")
merge_ewg_data()

def extract_text_from_image(image_file):
    try:
        # Read image
        image = Image.open(io.BytesIO(image_file.read()))
        
        # Perform OCR
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        print(f"Error extracting text: {e}")
        return None

def analyze_ingredients(text):
    if not text:
        return []
    
    # Split text into ingredients
    ingredients = [i.strip() for i in text.split(',')]
    results = []
    
    for ingredient in ingredients:
        if not ingredient:
            continue
            
        # Use ML model to predict
        prediction = ml_classifier.predict(ingredient)
        if prediction:
            results.append({
                'ingredient': ingredient,
                'is_harmful': prediction['is_harmful'],
                'confidence': prediction['confidence'],
                'category': prediction.get('category', 'Unknown'),
                'chemical_score': prediction.get('chemical_score', 0)
            })
    
    return results

# Serve frontend files
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/analyze-ingredients', methods=['POST'])
def analyze_product():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
            
        image_file = request.files['image']
        if not image_file:
            return jsonify({'error': 'Empty image file'}), 400
            
        # Extract text from image
        text = extract_text_from_image(image_file)
        if not text:
            return jsonify({'error': 'Could not extract text from image'}), 400
            
        # Analyze ingredients
        results = analyze_ingredients(text)
        if not results:
            return jsonify({'error': 'No ingredients found in image'}), 400
            
        return jsonify({
            'ingredients': results,
            'extracted_text': text
        })
        
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/test-connection')
def test_connection():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
