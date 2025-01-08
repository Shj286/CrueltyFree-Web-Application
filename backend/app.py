from flask import Flask, request, jsonify
from flask_cors import CORS
import tensorflow as tf
from PIL import Image
import numpy as np
import pytesseract
import re
import requests

app = Flask(__name__)
CORS(app)

# OpenFDA API Configuration
FDA_API_KEY = 'CD7MqpX5cZBUqEnUeYvYtrpvAfDkONGyjoghoNpB'
FDA_BASE_URL = 'https://api.fda.gov/drug/event.json'

# Explicitly set Tesseract path
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

# Comment out model loading for now
# model = tf.keras.models.load_model('model.h5')

def extract_ingredients_from_image(image):
    # Extract text from image using pytesseract
    try:
        text = pytesseract.image_to_string(image)
        if not text.strip():
            return "No text detected in image"
        
        # Try to find the ingredients section
        patterns = [
            r"INGREDIENTS:?(.*?)(?:\.|$)",
            r"CONTAINS:?(.*?)(?:\.|$)",
            r"COMPOSITION:?(.*?)(?:\.|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return text.strip()
    except Exception as e:
        return f"Error in OCR: {str(e)}"

def analyze_ingredients(ingredients_text):
    try:
        # Split ingredients into a list
        ingredients_list = [i.strip() for i in re.split(r'[,;]', ingredients_text)]
        
        harmful_ingredients = []
        safe_ingredients = []
        
        for ingredient in ingredients_list:
            if not ingredient:  # Skip empty strings
                continue
                
            # Query OpenFDA API for each ingredient
            params = {
                'api_key': FDA_API_KEY,
                'search': f'patient.drug.openfda.substance_name:"{ingredient}"',
                'limit': 1
            }
            
            try:
                response = requests.get(FDA_BASE_URL, params=params)
                data = response.json()
                
                # Check if there are any adverse events reported
                if 'results' in data and len(data['results']) > 0:
                    harmful_ingredients.append({
                        'ingredient': ingredient,
                        'category': 'FDA Reported',
                        'reason': 'Has reported adverse events in FDA database'
                    })
                else:
                    safe_ingredients.append(ingredient)
                    
            except Exception as e:
                print(f"Error checking ingredient {ingredient}: {str(e)}")
                continue
        
        # Also check against our local database for common harmful ingredients
        local_harmful = {
            'parabens': ['methylparaben', 'propylparaben', 'butylparaben', 'ethylparaben'],
            'phthalates': ['deh', 'dbp', 'bbp'],
            'formaldehyde': ['formaldehyde', 'quaternium-15', 'dmdm hydantoin', 'imidazolidinyl urea'],
            'sulfates': ['sodium lauryl sulfate', 'sodium laureth sulfate'],
            'triclosan': ['triclosan'],
            'toluene': ['toluene'],
            'propylene glycol': ['propylene glycol'],
            'synthetic fragrances': ['fragrance', 'parfum', 'perfume']
        }
        
        # Check against local database
        ingredients_lower = ingredients_text.lower()
        for category, ingredients in local_harmful.items():
            for ingredient in ingredients:
                if ingredient in ingredients_lower:
                    harmful_ingredients.append({
                        'ingredient': ingredient,
                        'category': category,
                        'reason': 'Known harmful ingredient'
                    })
        
        return {
            'harmful_ingredients': harmful_ingredients,
            'safe_ingredients': safe_ingredients,
            'total_ingredients': len(ingredients_list),
            'harmful_count': len(harmful_ingredients)
        }
        
    except Exception as e:
        return {
            'error': f"Error analyzing ingredients: {str(e)}",
            'harmful_ingredients': [],
            'safe_ingredients': [],
            'total_ingredients': 0,
            'harmful_count': 0
        }

@app.route('/analyze-ingredients', methods=['POST'])
def analyze_ingredients_route():
    try:
        file = request.files['image']
        image = Image.open(file.stream)
        
        # Extract ingredients from image
        ingredients_text = extract_ingredients_from_image(image)
        
        # Analyze ingredients
        analysis_result = analyze_ingredients(ingredients_text)
        
        return jsonify({
            'ingredients_text': ingredients_text,
            'analysis': analysis_result,
            'is_safe': len(analysis_result['harmful_ingredients']) == 0
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
