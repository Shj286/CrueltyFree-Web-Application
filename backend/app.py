from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from ingredient_api import load_database, merge_ewg_data
from ml_classifier import IngredientMLClassifier
import os
from PIL import Image
import pytesseract
import io
import traceback
import re

app = Flask(__name__, static_folder='../frontend')
CORS(app)

# Get the absolute path to the database file
DB_PATH = os.path.join(os.path.dirname(__file__), 'toxic_chemicals_database.json')

# Load database
print("Loading database from:", DB_PATH)
harmful_ingredients, safe_alternatives, toxicity_categories = load_database()

# Initialize ML classifier with database
ml_classifier = IngredientMLClassifier(harmful_ingredients, safe_alternatives)
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

def extract_ingredients_from_text(text):
    """Extract only valid ingredients from text."""
    # Common non-ingredient words and invalid patterns
    non_ingredients = {
        # Common text patterns
        'ingredients', 'contains', 'may', 'manufactured', 'facility', 'warning',
        'directions', 'use', 'caution', 'storage', 'keep', 'away', 'children',
        'safety', 'sealed', 'made', 'distributed', 'product', 'contact', 'email',
        'website', 'address', 'phone', 'www', 'com', 'road', 'street', 'ltd',
        'inc', 'limited', 'corporation',
        
        # Locations and addresses
        'avenue', 'boulevard', 'lane', 'drive', 'place', 'court', 'circle',
        'suite', 'floor', 'unit', 'building', 'block',
        
        # Common business terms
        'company', 'industries', 'enterprises', 'group', 'international',
        'worldwide', 'global', 'solutions', 'services',
        
        # Contact information
        'tel', 'telephone', 'fax', 'email', 'website', 'customer', 'service',
        'support', 'help', 'info', 'contact', 'us',
        
        # Measurements and quantities
        'mg', 'ml', 'oz', 'gram', 'percent', 'daily', 'value',
        
        # Other non-ingredient terms
        'best', 'before', 'date', 'batch', 'lot', 'number', 'expiry',
        'expires', 'manufactured', 'date', 'packaging'
    }
    
    # Split by common separators and clean
    parts = re.split(r'[,;:()\[\]]', text.lower())
    
    ingredients = []
    for part in parts:
        # Clean the text
        cleaned = part.strip()
        words = cleaned.split()
        
        # Skip invalid entries
        if any([
            not cleaned,  # Empty string
            not words,  # Empty word list
            len(cleaned) <= 1,  # Single characters
            cleaned.isdigit(),  # Just numbers
            len(words) > 4,  # Too many words (likely not an ingredient)
            '@' in cleaned,  # Email addresses
            'www.' in cleaned,  # Websites
            '.com' in cleaned,  # Websites
            cleaned.startswith('http'),  # URLs
            re.match(r'^[0-9-+()]+$', cleaned),  # Phone numbers
            re.match(r'^[0-9]+[A-Za-z\s]', cleaned),  # Street numbers
            re.match(r'.*\d+.*', cleaned),  # Contains numbers
            any(word in non_ingredients for word in words),  # Contains non-ingredient words
            any(word.endswith(('road', 'street', 'ave', 'lane', 'dr', 'blvd')) for word in words),  # Addresses
            any(len(word) == 1 for word in words),  # Single letter words
            any(word.isupper() and len(word) > 2 for word in words)  # Acronyms/abbreviations
        ]):
            continue
            
        # Additional validation for ingredient-like words
        if all([
            not re.match(r'^[0-9%]+$', cleaned),  # Not just numbers and percentages
            not any(char.isdigit() for char in cleaned),  # No digits
            len(cleaned) > 2,  # More than 2 characters
            not any(cleaned.startswith(prefix) for prefix in ['tel:', 'fax:', 'email:', 'http']),  # Not contact info
        ]):
            ingredients.append(cleaned)
    
    return ingredients

def analyze_ingredients(text):
    if not text:
        return []
    
    ingredients = extract_ingredients_from_text(text)
    results = []
    
    # Known safe ingredients with benefits
    known_safe = {
        'diethylamino hydroxybenzoyl hexyl benzoate': {
            'benefits': ['UV protection', 'Skin protection'],
            'common_uses': ['Sunscreens', 'Daily moisturizers'],
            'safety_notes': 'FDA approved UV filter'
        },
        'vitamin e': {
            'benefits': ['Antioxidant', 'Skin conditioning'],
            'common_uses': ['Anti-aging products', 'Moisturizers'],
            'safety_notes': 'Essential vitamin for skin health'
        },
        'aloe vera': {
            'benefits': ['Soothing', 'Moisturizing', 'Anti-inflammatory'],
            'common_uses': ['Skin care', 'After-sun care'],
            'safety_notes': 'Natural plant extract'
        },
        # Add more safe ingredients...
    }
    
    for ingredient in ingredients:
        normalized = ingredient.lower()
        
        # Check known safe ingredients
        if normalized in known_safe:
            safe_info = known_safe[normalized]
            results.append({
                'ingredient': ingredient,
                'is_harmful': False,
                'confidence': 1.0,
                'category': 'safe ingredients',
                'chemical_score': 0,
                'benefits': safe_info['benefits'],
                'common_uses': safe_info['common_uses'],
                'safety_notes': safe_info['safety_notes'],
                'research_links': {
                    'pubchem': f'https://pubchem.ncbi.nlm.nih.gov/#query={ingredient}',
                    'cosing': f'https://ec.europa.eu/growth/tools-databases/cosing/index.cfm?fuseaction=search.results&search={ingredient}'
                }
            })
            continue
            
        # Check against harmful database
        if ingredient in harmful_ingredients:
            info = harmful_ingredients[ingredient]
            is_truly_harmful = info['score'] >= 7
            
            results.append({
                'ingredient': ingredient,
                'is_harmful': is_truly_harmful,
                'confidence': 1.0,
                'category': info.get('categories', ['Unknown'])[0],
                'chemical_score': info.get('score', 5),
                'concerns': info.get('concerns', []) if is_truly_harmful else [],
                'found_in': info.get('found_in', []),
                'alternatives': get_safe_alternatives(ingredient) if is_truly_harmful else [],
                'research_links': get_research_links(ingredient)
            })
            continue
            
        # For unknown ingredients, provide research links instead of AI warning
        results.append({
            'ingredient': ingredient,
            'is_harmful': False,  # Default to safe if unknown
            'confidence': 0.7,
            'category': 'Unknown',
            'research_links': {
                'pubchem': f'https://pubchem.ncbi.nlm.nih.gov/#query={ingredient}',
                'cosing': f'https://ec.europa.eu/growth/tools-databases/cosing/index.cfm?fuseaction=search.results&search={ingredient}',
                'google_scholar': f'https://scholar.google.com/scholar?q={ingredient}+cosmetic+safety',
                'fda': f'https://www.fda.gov/search?s={ingredient}',
                'inci': f'https://incidecoder.com/ingredients/{ingredient.replace(" ", "-")}'
            },
            'note': 'Please check official sources for detailed information about this ingredient.'
        })
    
    return results

def get_research_links(ingredient):
    """Get comprehensive research links for an ingredient."""
    return {
        'pubchem': f'https://pubchem.ncbi.nlm.nih.gov/#query={ingredient}',
        'cosing': f'https://ec.europa.eu/growth/tools-databases/cosing/index.cfm?fuseaction=search.results&search={ingredient}',
        'google_scholar': f'https://scholar.google.com/scholar?q={ingredient}+cosmetic+safety',
        'fda': f'https://www.fda.gov/search?s={ingredient}',
        'inci': f'https://incidecoder.com/ingredients/{ingredient.replace(" ", "-")}',
        'ewg': f'https://www.ewg.org/skindeep/search/?search={ingredient}'
    }

def get_regulatory_info(ingredient):
    """Get regulatory information for an ingredient."""
    return {
        'fda_status': 'Approved for cosmetic use',  # You can expand this
        'eu_status': 'Allowed in cosmetics',  # You can expand this
        'restrictions': toxicity_categories.get(ingredient, {}).get('restrictions', [])
    }

def get_common_uses(ingredient):
    """Get common uses for an ingredient."""
    # You can expand this with a proper database
    return [
        'Skin care products',
        'Hair care products',
        'Cosmetics'
    ]

def get_safe_alternatives(ingredient):
    """Get safe alternatives for a harmful ingredient."""
    try:
        # First check direct matches in safe alternatives
        if ingredient in safe_alternatives:
            return safe_alternatives[ingredient]
        
        # Then check category-based alternatives
        category = ml_classifier.get_ingredient_category(ingredient)
        alternatives = safe_alternatives.get(category, [])
        
        # If no specific alternatives found, try general alternatives
        if not alternatives and category != 'general':
            alternatives = safe_alternatives.get('general', [])
            
        return alternatives
        
    except Exception as e:
        print(f"Error getting alternatives for {ingredient}: {e}")
        return []

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
        print(traceback.format_exc())  # Log the full error
        return jsonify({'error': str(e)}), 500

@app.route('/test-connection')
def test_connection():
    return jsonify({'status': 'ok'})

@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        # Process image and get ingredients
        image = Image.open(file)
        text = pytesseract.image_to_string(image)
        
        # Analyze ingredients
        results = analyze_ingredients(text)
        
        return jsonify({
            'text': text,
            'analysis': results
        })
    except Exception as e:
        print(traceback.format_exc())  # Log the full error
        return jsonify({'error': str(e)}), 500

# Add a test endpoint
@app.route('/test', methods=['GET'])
def test():
    return jsonify({'status': 'Backend is running'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
