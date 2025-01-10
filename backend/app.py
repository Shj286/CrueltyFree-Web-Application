from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from PIL import Image, ImageOps, ImageEnhance
import pytesseract
from ingredient_api import ingredient_api
import tempfile
import re

app = Flask(__name__, static_folder='../frontend')
CORS(app, resources={r"/*": {
    "origins": "*",  # Allow all origins for now
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "max_age": 3600
}})

# Serve frontend files
@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return app.send_static_file('index.html')

app.register_blueprint(ingredient_api, url_prefix='/api')

def load_toxic_database():
    try:
        # Get the absolute path to the database file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        database_path = os.path.join(current_dir, 'toxic_chemicals_database.json')
        
        print(f"Loading database from: {database_path}")  # Debug log
        
        with open(database_path, 'r') as f:
            data = json.load(f)
            if not data or 'harmful_ingredients' not in data:
                print("Warning: Database file is empty or missing harmful_ingredients")
                return {'harmful_ingredients': {}}
            print(f"Successfully loaded {len(data['harmful_ingredients'])} harmful ingredients")
            return data
    except FileNotFoundError:
        print(f"Error: Database file not found at {database_path}")
        return {'harmful_ingredients': {}}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in database file: {e}")
        return {'harmful_ingredients': {}}
    except Exception as e:
        print(f"Error loading database: {e}")
        return {'harmful_ingredients': {}}

def preprocess_image(image):
    """Enhanced image preprocessing for better OCR accuracy."""
    try:
        # Convert to grayscale
        image = image.convert('L')
        
        # Increase contrast and sharpness
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Resize if too small or too large
        target_width = 2000  # Optimal width for OCR
        if image.size[0] < 1000 or image.size[0] > 3000:
            ratio = target_width / image.size[0]
            new_size = (target_width, int(image.size[1] * ratio))
            image = image.resize(new_size, Image.LANCZOS)
        
        # Apply threshold to make text more clear
        from PIL import ImageOps
        image = ImageOps.autocontrast(image, cutoff=1)
        
        return image
    except Exception as e:
        print(f"Error preprocessing image: {e}")
        return image

def clean_ingredient_text(text):
    """Enhanced ingredient text cleaning and normalization."""
    # Remove common prefixes and headers
    text = re.sub(r'^.*?(ingredients|contains|ingr\.|composition|ingredients:).*?:', '', text, flags=re.IGNORECASE)
    
    # Replace various separators with commas
    text = re.sub(r'[;|•|\n|/|\\|\|]', ',', text)
    
    # Remove parentheses and their contents (but keep important chemical names)
    text = re.sub(r'\([^)]*?(%|w/w|v/v|color|colour|ci|no\.)\s*[^)]*\)', '', text, flags=re.IGNORECASE)
    
    # Split by comma and clean each ingredient
    ingredients = []
    for ingredient in text.split(','):
        ingredient = ingredient.strip()
        if ingredient and len(ingredient) > 1:
            # Remove percentage numbers and units
            ingredient = re.sub(r'\d+(\.\d+)?(\s*%|\s*ppm|\s*w/w|\s*v/v)?', '', ingredient)
            # Remove special characters but keep hyphens and periods in chemical names
            ingredient = re.sub(r'[^\w\s\-\.]', '', ingredient)
            # Remove extra spaces
            ingredient = ' '.join(ingredient.split())
            # Remove common prefixes/suffixes
            ingredient = re.sub(r'^(and|or|with|contains|also)\s+', '', ingredient, flags=re.IGNORECASE)
            ingredient = re.sub(r'\s+(and|or|with|contains|also)$', '', ingredient, flags=re.IGNORECASE)
            
            if ingredient and len(ingredient) > 1:
                ingredients.append(ingredient)
    
    # Remove duplicates while preserving order
    seen = set()
    ingredients = [x for x in ingredients if not (x.lower() in seen or seen.add(x.lower()))]
    
    print(f"Found {len(ingredients)} unique ingredients: {ingredients}")  # Debug log
    return ingredients

def extract_text_from_image(image_file):
    """Enhanced text extraction with improved accuracy."""
    try:
        # Create a temporary file to save the uploaded image
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            temp_path = temp_file.name
            
        # Save and open the image
        image_file.save(temp_path)
        image = Image.open(temp_path)
        
        # Preprocess the image
        processed_image = preprocess_image(image)
        
        # Configure OCR settings for better accuracy
        custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1 -l eng --dpi 300'
        
        # Try multiple OCR passes with different preprocessing
        texts = []
        
        # First pass: Normal processed image
        texts.append(pytesseract.image_to_string(processed_image, config=custom_config))
        
        # Second pass: Inverted image
        inverted_image = ImageOps.invert(processed_image)
        texts.append(pytesseract.image_to_string(inverted_image, config=custom_config))
        
        # Third pass: Different PSM mode
        custom_config_alt = r'--oem 3 --psm 4 -c preserve_interword_spaces=1 -l eng --dpi 300'
        texts.append(pytesseract.image_to_string(processed_image, config=custom_config_alt))
        
        # Clean up
        os.unlink(temp_path)
        
        # Combine and clean results
        combined_text = ' '.join(texts)
        ingredients = clean_ingredient_text(combined_text)
        
        if not ingredients:
            raise ValueError("No ingredients could be extracted from the image. Please ensure the image is clear and contains readable ingredient text.")
        
        return ingredients
    except Exception as e:
        print(f"Error in OCR: {e}")
        raise ValueError(f"Failed to process image: {str(e)}")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Server is running'}), 200

@app.route('/analyze-ingredients', methods=['POST'])
def analyze_ingredients():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        image_file = request.files['image']
        if not image_file:
            return jsonify({'error': 'Empty file'}), 400
            
        # Validate file type
        if not image_file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            return jsonify({'error': 'Invalid file type. Please upload a PNG or JPEG image'}), 400

        # Extract ingredients from image
        try:
            ingredients = extract_text_from_image(image_file)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # Load toxic database
        toxic_db = load_toxic_database()
        
        harmful_ingredients = []
        safe_ingredients = []
        detailed_harmful = []

        # Analyze each ingredient
        for ingredient in ingredients:
            ingredient_lower = ingredient.lower()
            found_harmful = False
            
            # Check against harmful ingredients database
            for harmful_name, info in toxic_db['harmful_ingredients'].items():
                # Check main name
                if ingredient_lower in harmful_name.lower():
                    detailed_harmful.append({
                        "name": ingredient,
                        "score": info.get("score", 5),
                        "concerns": info.get("concerns", []),
                        "categories": info.get("categories", []),
                        "alternatives": info.get("safe_alternatives", [])
                    })
                    harmful_ingredients.append(ingredient)
                    found_harmful = True
                    break
                
                # Check alternative names
                for alt_name in info.get("alternative_names", []):
                    if ingredient_lower in alt_name.lower():
                        detailed_harmful.append({
                            "name": ingredient,
                            "score": info.get("score", 5),
                            "concerns": info.get("concerns", []),
                            "categories": info.get("categories", []),
                            "alternatives": info.get("safe_alternatives", [])
                        })
                        harmful_ingredients.append(ingredient)
                        found_harmful = True
                        break
                
                if found_harmful:
                    break
            
            if not found_harmful:
                safe_ingredients.append(ingredient)

        return jsonify({
            'success': True,
            'safe_ingredients': safe_ingredients,
            'harmful_ingredients': harmful_ingredients,
            'detailed_harmful': detailed_harmful,
            'total_ingredients': len(ingredients)
        })

    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({'error': str(e)}), 500

# Add error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(error):
    return jsonify({'error': str(error)}), 500

# Add connection test endpoint
@app.route('/test-connection', methods=['GET', 'OPTIONS'])
def test_connection():
    return jsonify({'status': 'connected', 'message': 'Server is reachable'}), 200

if __name__ == '__main__':
    # Check if frontend directory exists
    if not os.path.exists(app.static_folder):
        print(f"Warning: Frontend directory not found at {app.static_folder}")
    
    # Check if tesseract is installed
    try:
        pytesseract.get_tesseract_version()
        print("Tesseract version:", pytesseract.get_tesseract_version())
    except Exception as e:
        print("Warning: Tesseract is not properly installed. OCR functionality may not work.")
        print("Error:", str(e))
    
    print("Server starting on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
