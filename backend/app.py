from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import pytesseract
import re
import os
from ingredient_scraper import IngredientAnalyzer
import socket

app = Flask(__name__)
# Configure CORS to allow requests from any origin
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Initialize the analyzer
analyzer = IngredientAnalyzer()

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

def preprocess_image(image):
    """Enhanced image preprocessing for better OCR results."""
    # Convert to RGB if not already
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Resize image to improve readability
    width, height = image.size
    if width < 1000:  # Only resize if image is too small
        ratio = 1000.0 / width
        new_size = (int(width * ratio), int(height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    
    # Convert to grayscale
    gray = image.convert('L')
    
    # Enhance contrast and sharpness
    from PIL import ImageEnhance
    
    # Enhance contrast
    contrast = ImageEnhance.Contrast(gray)
    gray = contrast.enhance(2.0)
    
    # Enhance sharpness
    sharpness = ImageEnhance.Sharpness(gray)
    gray = sharpness.enhance(2.0)
    
    # Enhance brightness
    brightness = ImageEnhance.Brightness(gray)
    gray = brightness.enhance(1.2)
    
    return gray

@app.route('/analyze-ingredients', methods=['POST'])
def analyze_ingredients():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
            
        file = request.files['image']
        image = Image.open(file.stream)
        
        # Preprocess image for better OCR
        processed_image = preprocess_image(image)
        
        # Try multiple OCR configurations to get best results
        configs = [
            '--psm 6 --oem 3 -c preserve_interword_spaces=1',  # Assume uniform block of text
            '--psm 4 --oem 3 -c preserve_interword_spaces=1',  # Assume single column
            '--psm 3 --oem 3 -c preserve_interword_spaces=1'   # Fully automatic page segmentation
        ]
        
        texts = []
        for config in configs:
            text = pytesseract.image_to_string(processed_image, config=config)
            texts.append(text)
        
        # Use the text with the most ingredients found
        ingredients_sections = [extract_ingredients_section(t) for t in texts]
        ingredients_lists = [clean_ingredients(t) for t in ingredients_sections if t]
        
        # Choose the result with the most ingredients
        if not ingredients_lists:
            return jsonify({'error': 'No ingredients found in the image'}), 400
            
        ingredients_text = max(ingredients_sections, key=lambda x: len(clean_ingredients(x)))
        ingredients_list = clean_ingredients(ingredients_text)
        
        print(f"OCR Results:")
        print(f"Original texts: {texts}")
        print(f"Ingredients sections: {ingredients_sections}")
        print(f"Final ingredients list: {ingredients_list}")
        
        # Analyze ingredients
        analysis = analyzer.analyze_ingredients(ingredients_text)
        
        response_data = {
            'original_texts': texts,
            'ingredients_found': ingredients_list,
            'analysis_results': {
                'total_ingredients': len(ingredients_list),
                'harmful_ingredients_found': len(analysis['harmful_ingredients']),
                'safety_score': analysis['safety_score'],
                'safety_level': get_safety_level(analysis['safety_score']),
                'harmful_details': analysis['harmful_ingredients'],
                'safe_ingredients': analysis['safe_ingredients']
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        return jsonify({'error': str(e)}), 400

def extract_ingredients_section(text):
    """Extract ingredients section from text."""
    patterns = [
        r"INGREDIENTS:?(.*?)(?:\.|$)",
        r"CONTAINS:?(.*?)(?:\.|$)",
        r"COMPOSITION:?(.*?)(?:\.|$)",
        r"INGREDIENTS/INGRÉDIENTS:?(.*?)(?:\.|$)",
        r"INGREDIENTS/成分:?(.*?)(?:\.|$)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    
    return text.strip()

def clean_ingredients(text):
    """Clean and split ingredients text into a list."""
    # Remove common unnecessary text
    text = re.sub(r'\([^)]*\)', '', text)  # Remove content in parentheses
    text = re.sub(r'\b(may contain|contains|ingredients|ingrédients)\b', '', text, flags=re.IGNORECASE)
    
    # Split by common delimiters
    ingredients = re.split(r'[,;.]', text)
    
    # Clean each ingredient
    cleaned = []
    for ingredient in ingredients:
        ingredient = ingredient.strip()
        if ingredient and len(ingredient) > 1:  # Ignore empty or single-character strings
            cleaned.append(ingredient)
    
    return cleaned

def get_safety_level(score):
    """Get detailed safety level description."""
    if score >= 90:
        return {
            'level': 'Very Safe',
            'description': 'Product contains minimal to no harmful ingredients'
        }
    elif score >= 70:
        return {
            'level': 'Generally Safe',
            'description': 'Product contains few potentially concerning ingredients'
        }
    elif score >= 50:
        return {
            'level': 'Moderate Concern',
            'description': 'Several potentially harmful ingredients detected'
        }
    elif score >= 30:
        return {
            'level': 'High Concern',
            'description': 'Multiple harmful ingredients found, consider alternatives'
        }
    else:
        return {
            'level': 'Very High Concern',
            'description': 'High concentration of harmful ingredients, strongly consider alternatives'
        }

# Add a health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Server is running'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)
