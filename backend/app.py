from flask import Flask, request, jsonify
from flask_cors import CORS
import tensorflow as tf
from PIL import Image
import numpy as np
import pytesseract
import re

app = Flask(__name__)
CORS(app)

# Comment out model loading for now
# model = tf.keras.models.load_model('model.h5')

# Mac Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'/opt/homebrew/bin/tesseract'  # For Mac

def extract_ingredients_from_image(image):
    # Extract text from image using pytesseract
    text = pytesseract.image_to_string(image)
    
    # Try to find the ingredients section
    # Common patterns in ingredient lists
    patterns = [
        r"INGREDIENTS:?(.*?)(?:\.|$)",
        r"CONTAINS:?(.*?)(?:\.|$)",
        r"COMPOSITION:?(.*?)(?:\.|$)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    # If no specific ingredients section found, return all text
    return text.strip()

def analyze_ingredients(ingredients_text):
    # List of common harmful ingredients
    harmful_ingredients = {
        'parabens': ['methylparaben', 'propylparaben', 'butylparaben', 'ethylparaben'],
        'phthalates': ['deh', 'dbp', 'bbp'],
        'formaldehyde': ['formaldehyde', 'quaternium-15', 'dmdm hydantoin', 'imidazolidinyl urea'],
        'sulfates': ['sodium lauryl sulfate', 'sodium laureth sulfate'],
        'triclosan': ['triclosan'],
        'toluene': ['toluene'],
        'propylene glycol': ['propylene glycol'],
        'synthetic fragrances': ['fragrance', 'parfum', 'perfume']
    }
    
    found_harmful = []
    ingredients_lower = ingredients_text.lower()
    
    for category, ingredients in harmful_ingredients.items():
        for ingredient in ingredients:
            if ingredient in ingredients_lower:
                found_harmful.append({
                    'category': category,
                    'ingredient': ingredient
                })
    
    return found_harmful

@app.route('/analyze-ingredients', methods=['POST'])
def analyze_ingredients_route():
    try:
        file = request.files['image']
        image = Image.open(file.stream)
        
        # Extract ingredients from image
        ingredients_text = extract_ingredients_from_image(image)
        
        # Analyze ingredients
        harmful_ingredients = analyze_ingredients(ingredients_text)
        
        return jsonify({
            'ingredients_text': ingredients_text,
            'harmful_ingredients': harmful_ingredients,
            'is_safe': len(harmful_ingredients) == 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Comment out or remove the predict route since we don't have the model
'''
@app.route('/predict', methods=['POST'])
def predict():
    try:
        file = request.files['image']
        image = Image.open(file.stream)
        processed_image = preprocess_image(image)
        
        # Predict with the model
        predictions = model.predict(processed_image)
        prediction_label = "Cruelty-Free" if predictions[0][0] > 0.5 else "Not Cruelty-Free"
        
        return jsonify({'prediction': prediction_label})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
'''

if __name__ == '__main__':
    app.run(debug=True)
