from flask import Blueprint, jsonify, request
from ingredient_scraper import IngredientAnalyzer, EWGScraper
import threading
import time
import json
import os
import requests
from bs4 import BeautifulSoup
from threading import Thread
import random
from datetime import datetime

ingredient_api = Blueprint('ingredient_api', __name__)
analyzer = IngredientAnalyzer()
ewg_scraper = EWGScraper()

def scrape_ewg_data(ingredient_name):
    """Scrape ingredient data from EWG's Skin Deep database."""
    try:
        # Format the search URL
        search_url = f"https://www.ewg.org/skindeep/search/?search={ingredient_name.replace(' ', '+')}"
        
        # Add headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        
        # Make request with delay to respect rate limits
        time.sleep(random.uniform(1, 3))
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find ingredient data
        ingredient_data = {
            'name': ingredient_name,
            'score': None,
            'hazard_score': None,
            'concerns': [],
            'found_in': [],
            'last_updated': datetime.now().isoformat()
        }
        
        # Extract hazard score (0-10)
        hazard_element = soup.find('div', class_='hazard-score')
        if hazard_element:
            ingredient_data['hazard_score'] = int(hazard_element.text.strip())
        
        # Extract health concerns
        concerns = soup.find_all('div', class_='health-concerns')
        if concerns:
            ingredient_data['concerns'] = [c.text.strip() for c in concerns]
        
        # Extract product types
        products = soup.find_all('div', class_='product-types')
        if products:
            ingredient_data['found_in'] = [p.text.strip() for p in products]
        
        return ingredient_data
        
    except Exception as e:
        print(f"Error scraping EWG data for {ingredient_name}: {e}")
        return None

def merge_ewg_data():
    """Periodically update database with EWG data."""
    try:
        # Use absolute path
        db_path = os.path.join(os.path.dirname(__file__), 'toxic_chemicals_database.json')
        
        # Create file if it doesn't exist
        if not os.path.exists(db_path):
            initial_data = {
                "harmful_ingredients": {},
                "safe_alternatives": {},
                "toxicity_categories": {}
            }
            with open(db_path, 'w') as f:
                json.dump(initial_data, f, indent=4)
        
        # Load current database
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        # Track updates
        updates_made = False
        
        # Update harmful ingredients with EWG data
        for ingredient_name in database['harmful_ingredients'].keys():
            if 'ewg_last_updated' not in database['harmful_ingredients'][ingredient_name] or \
               (datetime.now() - datetime.fromisoformat(database['harmful_ingredients'][ingredient_name]['ewg_last_updated'])).days > 7:
                
                print(f"Updating EWG data for {ingredient_name}...")
                ewg_data = scrape_ewg_data(ingredient_name)
                
                if ewg_data:
                    database['harmful_ingredients'][ingredient_name].update({
                        'ewg_score': ewg_data['hazard_score'],
                        'ewg_concerns': ewg_data['concerns'],
                        'ewg_found_in': ewg_data['found_in'],
                        'ewg_last_updated': ewg_data['last_updated']
                    })
                    updates_made = True
                
                # Add delay between requests
                time.sleep(random.uniform(2, 5))
        
        # Save updated database if changes were made
        if updates_made:
            with open(db_path, 'w') as f:
                json.dump(database, f, indent=4)
            print("Database updated with EWG data")
            
        return True
        
    except Exception as e:
        print(f"Error updating EWG data: {e}")
        return False

def load_database():
    """Load the ingredient database."""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'toxic_chemicals_database.json')
        
        # Create file if it doesn't exist
        if not os.path.exists(db_path):
            initial_data = {
                "harmful_ingredients": {},
                "safe_alternatives": {},
                "toxicity_categories": {}
            }
            with open(db_path, 'w') as f:
                json.dump(initial_data, f, indent=4)
            return {}, {}, {}
            
        with open(db_path, 'r') as f:
            data = json.load(f)
            return (
                data.get('harmful_ingredients', {}),
                data.get('safe_alternatives', {}),
                data.get('toxicity_categories', {})
            )
    except Exception as e:
        print(f"Error loading database: {e}")
        return {}, {}, {}

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