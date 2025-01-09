from flask import Blueprint, jsonify, request
from ingredient_scraper import IngredientAnalyzer, EWGScraper
import threading
import schedule
import time
import json

ingredient_api = Blueprint('ingredient_api', __name__)
analyzer = IngredientAnalyzer()
ewg_scraper = EWGScraper()

def merge_ewg_data():
    """Merge EWG data with our toxic chemicals database"""
    try:
        ewg_data = ewg_scraper.get_all_ingredients()
        
        # Update existing ingredients with EWG data
        for name, info in ewg_data.items():
            if name.lower() in analyzer.harmful_ingredients:
                current_info = analyzer.harmful_ingredients[name.lower()]
                # Merge EWG concerns with existing concerns
                current_info['concerns'].extend([c for c in info.get('concerns', []) 
                                              if c not in current_info['concerns']])
                # Update score if EWG score is higher
                ewg_score = int(info.get('hazard_score', 0))
                if ewg_score > current_info['score']:
                    current_info['score'] = ewg_score
                # Add EWG specific data
                current_info['ewg_data'] = {
                    'ewg_score': info.get('hazard_score'),
                    'ewg_concerns': info.get('concerns', []),
                    'ewg_references': info.get('references', [])
                }
            else:
                # Add new harmful ingredient if EWG score is high enough
                if int(info.get('hazard_score', 0)) >= 6:
                    analyzer.harmful_ingredients[name.lower()] = {
                        'score': int(info.get('hazard_score', 0)),
                        'categories': info.get('categories', []),
                        'concerns': info.get('concerns', []),
                        'found_in': info.get('found_in', []),
                        'alternative_names': info.get('alternative_names', []),
                        'ewg_data': {
                            'ewg_score': info.get('hazard_score'),
                            'ewg_concerns': info.get('concerns', []),
                            'ewg_references': info.get('references', [])
                        }
                    }
        
        # Save updated database
        with open('/Users/shubham/CrueltyFree/backend/toxic_chemicals_database.json', 'w') as f:
            json.dump({
                'harmful_ingredients': analyzer.harmful_ingredients,
                'safe_alternatives': analyzer.safe_alternatives,
                'toxicity_categories': analyzer.toxicity_categories
            }, f, indent=4)
            
        print("Successfully merged EWG data with toxic chemicals database")
    except Exception as e:
        print(f"Error merging EWG data: {str(e)}")

def update_database_periodically():
    while True:
        print("Starting periodic database update...")
        merge_ewg_data()
        time.sleep(24 * 60 * 60)  # Update every 24 hours

# Start background thread for periodic updates
update_thread = threading.Thread(target=update_database_periodically)
update_thread.daemon = True
update_thread.start()

@ingredient_api.route('/ingredient/<name>', methods=['GET'])
def get_ingredient_info(name):
    """Get detailed information about a specific ingredient"""
    try:
        # First check our main database
        result = analyzer._check_ingredient(name)
        if result['is_harmful']:
            return jsonify(result)
        
        # If not found, try EWG database
        ewg_data = ewg_scraper.scrape_ingredient(name)
        if ewg_data:
            # Add to our database if hazardous
            if int(ewg_data.get('hazard_score', 0)) >= 6:
                merge_ewg_data()  # This will add the new ingredient
                # Recheck our database
                result = analyzer._check_ingredient(name)
                return jsonify(result)
            
            # Return EWG data even if not hazardous
            return jsonify({
                'is_harmful': False,
                'ewg_data': ewg_data,
                'score': int(ewg_data.get('hazard_score', 0)),
                'concerns': ewg_data.get('concerns', [])
            })
            
        return jsonify({
            'is_harmful': False,
            'message': 'Ingredient not found in any database',
            'score': 0
        })
    except Exception as e:
        return jsonify({'error': str(e), 'score': 0}), 500

@ingredient_api.route('/ingredients/harmful', methods=['GET'])
def get_harmful_ingredients():
    """Get all harmful ingredients from both databases"""
    try:
        # Get harmful ingredients from our database
        harmful_ingredients = {
            name: info for name, info in analyzer.harmful_ingredients.items()
            if info['score'] >= 6
        }
        
        # Add any additional harmful ingredients from EWG
        ewg_harmful = ewg_scraper.get_harmful_ingredients()
        for name, info in ewg_harmful.items():
            if name.lower() not in harmful_ingredients and int(info.get('hazard_score', 0)) >= 6:
                harmful_ingredients[name.lower()] = {
                    'score': int(info.get('hazard_score', 0)),
                    'concerns': info.get('concerns', []),
                    'categories': info.get('categories', []),
                    'source': 'EWG'
                }
        
        return jsonify(harmful_ingredients)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ingredient_api.route('/analyze', methods=['POST'])
def analyze_ingredients():
    """Analyze a list of ingredients using both databases"""
    try:
        data = request.get_json()
        if not data or 'ingredients' not in data:
            return jsonify({'error': 'No ingredients provided'}), 400
            
        ingredients_text = data['ingredients']
        
        # Use our main analyzer
        analysis = analyzer.analyze_ingredients(ingredients_text)
        
        # Enhance with EWG data
        for ingredient in analysis['harmful_ingredients']:
            ewg_data = ewg_scraper.scrape_ingredient(ingredient['ingredient'])
            if ewg_data:
                ingredient['ewg_data'] = ewg_data
        
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500 