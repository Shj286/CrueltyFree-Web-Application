from flask import Flask, request, jsonify
from flask_cors import CORS
import tensorflow as tf
from PIL import Image
import numpy as np
import pytesseract
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Explicitly set Tesseract path
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

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
    # Expanded list of harmful ingredients by categories
    harmful_ingredients = {
        'parabens': [
            'methylparaben', 'propylparaben', 'butylparaben', 'ethylparaben',
            'isopropylparaben', 'isobutylparaben', 'benzylparaben'
        ],
        'phthalates': [
            'deh', 'dbp', 'bbp', 'dehp', 'dinp', 'didp', 'dnop', 'dibp',
            'diethyl phthalate', 'dimethyl phthalate', 'diisobutyl phthalate'
        ],
        'formaldehyde_releasers': [
            'formaldehyde', 'quaternium-15', 'dmdm hydantoin', 'imidazolidinyl urea',
            'diazolidinyl urea', 'polyoxymethylene urea', 'sodium hydroxymethylglycinate',
            'bromopol', '2-bromo-2-nitropropane-1,3-diol'
        ],
        'sulfates': [
            'sodium lauryl sulfate', 'sodium laureth sulfate', 'ammonium lauryl sulfate',
            'sodium coco sulfate', 'tea lauryl sulfate', 'sodium myreth sulfate'
        ],
        'chemical_sunscreens': [
            'oxybenzone', 'avobenzone', 'octisalate', 'octocrylene', 
            'homosalate', 'octinoxate', 'benzophenone', 'titanium dioxide',
            'zinc oxide nanoparticles', 'nano-titanium dioxide', 'tinosorb',
            'titanium oxide', 'nano-zinc oxide'
        ],
        'preservatives': [
            'triclosan', 'triclocarban', 'phenoxyethanol', 'chlorphenesin',
            'methylisothiazolinone', 'methylchloroisothiazolinone', 'bht', 'bha',
            'benzyl alcohol', 'potassium sorbate', 'sodium benzoate'
        ],
        'synthetic_colors': [
            'fd&c', 'yellow 5', 'red 40', 'blue 1', 'yellow 6', 
            'ci 19140', 'ci 42090', 'ci 15985', 'tartrazine',
            'carmine', 'carbon black', 'p-phenylenediamine'
        ],
        'synthetic_fragrances': [
            'fragrance', 'parfum', 'perfume', 'linalool', 'limonene', 
            'hydroxycitronellal', 'geraniol', 'citronellol', 'eugenol',
            'isoeugenol', 'benzyl benzoate', 'benzyl salicylate'
        ],
        'petroleum_derivatives': [
            'petrolatum', 'mineral oil', 'paraffin', 'petroleum jelly',
            'propylene glycol', 'isopropyl alcohol', 'toluene', 'benzene',
            'mineral oil', 'paraffinum liquidum', 'ceresin'
        ],
        'ethanolamines': [
            'diethanolamine', 'dea', 'tea', 'mea', 'triethanolamine',
            'monoethanolamine', 'cocamide dea', 'lauramide dea',
            'myristamide dea', 'oleamide dea', 'stearamide dea'
        ],
        'silicones': [
            'dimethicone', 'cyclomethicone', 'cyclopentasiloxane',
            'cyclotetrasiloxane', 'cyclohexasiloxane', 'trimethylsilylamodimethicone',
            'amodimethicone', 'dimethiconol'
        ],
        'heavy_metals': [
            'lead acetate', 'thimerosal', 'mercury', 'chromium',
            'hydrogenated cotton seed oil', 'aluminum chloride',
            'lead', 'arsenic', 'cadmium', 'nickel sulfate'
        ],
        'irritants_and_sensitizers': [
            'retinyl palmitate', 'retinol', 'retinoic acid',
            'hydroquinone', 'kojic acid', 'benzoyl peroxide',
            'salicylic acid in high concentrations', 'alpha-hydroxy acids',
            'beta-hydroxy acids', 'glycolic acid in high concentrations'
        ],
        'microplastics': [
            'polyethylene', 'polypropylene', 'polyamide', 'nylon-12',
            'nylon-6', 'polyethylene terephthalate', 'polymethyl methacrylate',
            'acrylates copolymer', 'polytetrafluoroethylene'
        ]
    }
    
    found_harmful = []
    ingredients_lower = ingredients_text.lower()
    
    # Add descriptions for why ingredients are harmful
    harmful_descriptions = {
        'parabens': 'May disrupt hormone function and have been linked to breast cancer',
        'phthalates': 'Potential endocrine disruptors that may affect reproductive health',
        'formaldehyde_releasers': 'Known carcinogen that can also cause skin irritation',
        'sulfates': 'Can cause skin and eye irritation, and strip natural oils',
        'chemical_sunscreens': 'May generate harmful free radicals and potentially cause cellular damage when exposed to UV light',
        'preservatives': 'Can cause skin irritation and allergic reactions',
        'synthetic_colors': 'May contain heavy metals and cause skin sensitivity',
        'synthetic_fragrances': 'Common allergens that can cause respiratory issues',
        'petroleum_derivatives': 'May be contaminated with carcinogens',
        'ethanolamines': 'Can form nitrosamines, which are carcinogenic',
        'silicones': 'Can trap bacteria and impurities in the skin',
        'heavy_metals': 'Can accumulate in the body and cause various health issues',
        'irritants_and_sensitizers': 'Can cause skin irritation, sensitivity, and photosensitivity',
        'microplastics': 'Environmental pollutants that can accumulate in the body and environment'
    }
    
    for category, ingredients in harmful_ingredients.items():
        for ingredient in ingredients:
            if ingredient in ingredients_lower:
                found_harmful.append({
                    'ingredient': ingredient,
                    'category': category,
                    'reason': harmful_descriptions.get(category, 'Potentially harmful ingredient')
                })
    
    # Additional analysis for ingredient combinations
    ingredient_list = [i.strip().lower() for i in re.split(r'[,;]', ingredients_text)]
    
    # Check for concerning combinations
    if any(p in ingredients_lower for p in harmful_ingredients['preservatives']) and \
       any(f in ingredients_lower for f in harmful_ingredients['synthetic_fragrances']):
        found_harmful.append({
            'ingredient': 'Preservative + Fragrance combination',
            'category': 'harmful_combination',
            'reason': 'This combination may increase skin sensitivity and irritation'
        })
    
    return {
        'harmful_ingredients': found_harmful,
        'total_ingredients_found': len(ingredient_list),
        'safety_score': max(0, 100 - (len(found_harmful) * 10)),  # Basic safety score
        'recommendations': get_recommendations(found_harmful)
    }

def get_recommendations(harmful_ingredients):
    recommendations = []
    categories_found = set(item['category'] for item in harmful_ingredients)
    
    alternatives = {
        'parabens': 'Look for products with natural preservatives like grapefruit seed extract or vitamin E',
        'sulfates': 'Try sulfate-free products with gentle cleansing agents like coco glucoside',
        'synthetic_fragrances': 'Choose fragrance-free products or those scented with essential oils',
        'petroleum_derivatives': 'Look for plant-based oils like jojoba, argan, or coconut oil',
        'preservatives': 'Consider products with natural preservatives like rosemary extract or neem oil',
        'chemical_sunscreens': 'Look for mineral sunscreens with non-nano zinc oxide or wear protective clothing',
        'irritants_and_sensitizers': 'Start with lower concentrations and patch test new products',
        'microplastics': 'Choose products with natural exfoliants like jojoba beads or ground nuts'
    }
    
    for category in categories_found:
        if category in alternatives:
            recommendations.append(alternatives[category])
    
    return recommendations

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
            'analysis': analysis_result,  # Now sending the complete analysis result
            'is_safe': len(analysis_result['harmful_ingredients']) == 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
