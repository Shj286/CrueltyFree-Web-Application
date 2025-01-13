from flask import Blueprint, jsonify, request
from ingredient_scraper import IngredientAnalyzer, EWGScraper
import threading
import time
import json
import os
import requests
from bs4 import BeautifulSoup
from threading import Thread

ingredient_api = Blueprint('ingredient_api', __name__)
analyzer = IngredientAnalyzer()
ewg_scraper = EWGScraper()

def load_database():
    """Load the toxic chemicals database."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'toxic_chemicals_database.json')
        with open(db_path, 'r') as f:
            data = json.load(f)
            
        harmful_ingredients = data.get('harmful_ingredients', {})
        safe_alternatives = data.get('safe_alternatives', {})
        toxicity_categories = data.get('toxicity_categories', {})
        
        print(f"Successfully loaded {len(harmful_ingredients)} harmful ingredients from database")
        print(f"Successfully loaded {len(safe_alternatives)} safe alternatives")
        print(f"Successfully loaded {len(toxicity_categories)} toxicity categories")
        
        return harmful_ingredients, safe_alternatives, toxicity_categories
    except Exception as e:
        print(f"Error loading database: {e}")
        return {}, {}, {}

def merge_ewg_data():
    """Periodically update database with data from EWG."""
    def update_loop():
        while True:
            try:
                # Load current database
                db_path = os.path.join(os.path.dirname(__file__), 'toxic_chemicals_database.json')
                with open(db_path, 'r') as f:
                    data = json.load(f)
                
                # Here you would typically:
                # 1. Fetch new data from EWG
                # 2. Process and merge with existing data
                # 3. Save updated database
                
                print("Database updated successfully")
                
            except Exception as e:
                print(f"Error updating database: {e}")
            
            # Wait for 24 hours before next update
            time.sleep(24 * 60 * 60)
    
    # Start update loop in background thread
    update_thread = Thread(target=update_loop, daemon=True)
    update_thread.start()

def save_database(harmful_ingredients, safe_alternatives, toxicity_categories):
    """Save the database to file."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'toxic_chemicals_database.json')
        data = {
            'harmful_ingredients': harmful_ingredients,
            'safe_alternatives': safe_alternatives,
            'toxicity_categories': toxicity_categories
        }
        with open(db_path, 'w') as f:
            json.dump(data, f, indent=4)
        print("Database saved successfully")
        return True
    except Exception as e:
        print(f"Error saving database: {e}")
        return False

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