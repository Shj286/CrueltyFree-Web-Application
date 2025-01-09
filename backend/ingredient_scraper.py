import json
import re

class IngredientAnalyzer:
    def __init__(self):
        self.load_database()

    def load_database(self):
        database_path = '/Users/shubham/CrueltyFree/backend/toxic_chemicals_database.json'
        try:
            with open(database_path, 'r') as f:
                data = json.load(f)
                self.harmful_ingredients = data.get('harmful_ingredients', {})
                self.safe_alternatives = data.get('safe_alternatives', {})
                self.toxicity_categories = data.get('toxicity_categories', {})
                print(f"Successfully loaded {len(self.harmful_ingredients)} harmful ingredients from database")
                print(f"Successfully loaded {len(self.safe_alternatives)} safe alternatives")
                print(f"Successfully loaded {len(self.toxicity_categories)} toxicity categories")
        except FileNotFoundError:
            print(f"Error: Database file not found at {database_path}")
            self.harmful_ingredients = {}
            self.safe_alternatives = {}
            self.toxicity_categories = {}
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in database file at {database_path}")
            self.harmful_ingredients = {}
            self.safe_alternatives = {}
            self.toxicity_categories = {}
        except Exception as e:
            print(f"Error loading database: {str(e)}")
            self.harmful_ingredients = {}
            self.safe_alternatives = {}
            self.toxicity_categories = {}

    def analyze_ingredients(self, ingredients_text):
        print("\n=== Starting Ingredient Analysis ===")
        print(f"Raw text: {ingredients_text}")
        
        # Clean and split ingredients
        ingredients_list = self.clean_ingredients(ingredients_text)
        print(f"\nCleaned ingredients ({len(ingredients_list)}): {ingredients_list}")
        
        harmful_found = []
        safe_ingredients = []
        categories_found = {}
        
        for ingredient in ingredients_list:
            print(f"\nAnalyzing ingredient: {ingredient}")
            result = self._check_ingredient(ingredient)
            print(f"Analysis result: {result}")
            
            if result['is_harmful']:
                harmful_found.append({
                    'ingredient': ingredient,
                    'score': result['score'],
                    'concerns': result['concerns'],
                    'categories': result['categories'],
                    'found_in': result['found_in'],
                    'matched_name': result['matched_name']
                })
                print(f"Found harmful ingredient: {ingredient} -> {result['matched_name']}")
                
                for category in result['categories']:
                    categories_found[category] = categories_found.get(category, 0) + 1
            else:
                safe_ingredients.append({
                    'ingredient': ingredient,
                    'score': 0
                })
                print(f"Ingredient appears safe: {ingredient}")
        
        print("\n=== Analysis Summary ===")
        print(f"Total ingredients: {len(ingredients_list)}")
        print(f"Harmful ingredients: {len(harmful_found)}")
        print(f"Categories found: {categories_found}")
        
        return {
            'harmful_ingredients': harmful_found,
            'safe_ingredients': safe_ingredients,
            'total_ingredients': len(ingredients_list),
            'safety_score': self._calculate_safety_score(harmful_found, len(ingredients_list)),
            'categories_found': categories_found,
            'category_descriptions': {k: self.toxicity_categories[k] 
                                   for k in categories_found.keys()}
        }

    def _check_ingredient(self, ingredient):
        ingredient_lower = ingredient.lower().strip()
        print(f"\nChecking ingredient: {ingredient}")
        
        # Common variations and normalizations
        variations_map = {
            'titanium_dioxide': ['titanium dioxide', 'titanium oxide', 'tio2', 'ci 77891', 'titania'],
            'zinc_oxide': ['zinc oxide', 'zno', 'ci 77947'],
            'iron_oxide': ['iron oxide', 'ci 77491', 'ci 77492', 'ci 77499'],
            'aluminum_compounds': ['aluminum chlorohydrate', 'aluminum zirconium', 'aluminum chloride', 'aluminum hydroxide'],
            'silica': ['silicon dioxide', 'sio2'],
            'octinoxate': ['ethylhexyl methoxycinnamate', 'octyl methoxycinnamate', 'emt', 'omc'],
            'polyethylene_glycols': ['peg-', 'polyethylene glycol'],
            'siloxanes': ['cyclopentasiloxane', 'cyclomethicone', 'cyclotetrasiloxane', 'dimethicone'],
            'benzophenone': ['benzophenone-1', 'benzophenone-2', 'benzophenone-3', 'oxybenzone'],
            'butylated_compounds': ['butylated hydroxyanisole', 'butylated hydroxytoluene'],
            'parabens': ['methylparaben', 'propylparaben', 'butylparaben', 'ethylparaben', 'isobutylparaben'],
            'phthalates': ['dibutyl phthalate', 'diethyl phthalate'],
            'formaldehyde_releasers': ['dmdm hydantoin', 'imidazolidinyl urea', 'diazolidinyl urea', 'quaternium-15'],
            'synthetic_fragrances': ['fragrance', 'parfum', 'aroma', 'denat alcohol']
        }
        
        # First try exact matching
        match = self._exact_match(ingredient_lower)
        if match['is_harmful']:
            print(f"Found exact match: {ingredient} -> {match['matched_name']}")
            return match
        
        # Normalize the ingredient name by removing spaces and special characters
        normalized_ingredient = re.sub(r'[^a-z0-9]', '', ingredient_lower)
        print(f"Normalized ingredient: {normalized_ingredient}")
        
        # Check for variations and partial matches with stricter rules
        for harmful_name, info in self.harmful_ingredients.items():
            harmful_lower = harmful_name.lower()
            
            # Convert harmful_name to match database key format
            harmful_key = harmful_lower.replace(' ', '_')
            
            # Check main name variations with exact matching
            variations = variations_map.get(harmful_key, [harmful_lower])
            for variation in variations:
                variation_lower = variation.lower()
                normalized_variation = re.sub(r'[^a-z0-9]', '', variation_lower)
                
                # Only match if it's an exact match or starts with the variation
                # This prevents partial matching that could lead to false positives
                if (variation_lower == ingredient_lower or 
                    ingredient_lower.startswith(variation_lower) or 
                    normalized_ingredient == normalized_variation):
                    print(f"Found variation match: {ingredient} -> {harmful_name} (via {variation})")
                    return {
                        'is_harmful': True,
                        'matched_name': harmful_name,
                        'score': info['score'],
                        'concerns': info['concerns'],
                        'categories': info['categories'],
                        'found_in': info['found_in']
                    }
            
            # Check alternative names with stricter matching
            for alt_name in info['alternative_names']:
                alt_lower = alt_name.lower()
                normalized_alt = re.sub(r'[^a-z0-9]', '', alt_lower)
                
                # Special case for PEG compounds
                if harmful_key == 'polyethylene_glycols':
                    if ingredient_lower.startswith('peg-') or 'polyethylene glycol' in ingredient_lower:
                        print(f"Found PEG compound match: {ingredient} -> {harmful_name}")
                        return {
                            'is_harmful': True,
                            'matched_name': harmful_name,
                            'score': info['score'],
                            'concerns': info['concerns'],
                            'categories': info['categories'],
                            'found_in': info['found_in']
                        }
                
                # Special case for siloxanes/silicones with strict matching
                if harmful_key == 'siloxanes':
                    if any(term in ingredient_lower for term in ['siloxane', 'cyclomethicone', 'dimethicone']):
                        print(f"Found siloxane match: {ingredient} -> {harmful_name}")
                        return {
                            'is_harmful': True,
                            'matched_name': harmful_name,
                            'score': info['score'],
                            'concerns': info['concerns'],
                            'categories': info['categories'],
                            'found_in': info['found_in']
                        }
                
                # Exact match or starts with for alternative names
                if (alt_lower == ingredient_lower or 
                    ingredient_lower.startswith(alt_lower)):
                    print(f"Found alternative name match: {ingredient} -> {harmful_name} (via {alt_name})")
                    return {
                        'is_harmful': True,
                        'matched_name': harmful_name,
                        'score': info['score'],
                        'concerns': info['concerns'],
                        'categories': info['categories'],
                        'found_in': info['found_in']
                    }
                
                # Check for compound ingredients (e.g., "titanium dioxide") with exact word matching
                if ' ' in alt_lower:
                    parts = alt_lower.split()
                    if (ingredient_lower == alt_lower or
                        (len(parts) > 1 and all(f" {part} " in f" {ingredient_lower} " for part in parts))):
                        print(f"Found compound match: {ingredient} -> {harmful_name} (via {alt_name})")
                        return {
                            'is_harmful': True,
                            'matched_name': harmful_name,
                            'score': info['score'],
                            'concerns': info['concerns'],
                            'categories': info['categories'],
                            'found_in': info['found_in']
                        }
        
        print(f"No harmful match found for: {ingredient}")
        return {
            'is_harmful': False,
            'matched_name': None,
            'score': 0,
            'concerns': [],
            'categories': [],
            'found_in': []
        }

    def _exact_match(self, ingredient):
        if ingredient in self.harmful_ingredients:
            info = self.harmful_ingredients[ingredient]
            return {
                'is_harmful': True,
                'matched_name': ingredient,
                'score': info['score'],
                'concerns': info['concerns'],
                'categories': info['categories'],
                'found_in': info['found_in']
            }
        return {'is_harmful': False}

    def _partial_match(self, ingredient):
        min_length = 4  # Minimum length to consider for partial matching
        for harmful_name, info in self.harmful_ingredients.items():
            if len(harmful_name) >= min_length and harmful_name in ingredient:
                return {
                    'is_harmful': True,
                    'matched_name': harmful_name,
                    'score': info['score'],
                    'concerns': info['concerns'],
                    'categories': info['categories'],
                    'found_in': info['found_in']
                }
            for alt_name in info['alternative_names']:
                if len(alt_name) >= min_length and alt_name.lower() in ingredient:
                    return {
                        'is_harmful': True,
                        'matched_name': harmful_name,
                        'score': info['score'],
                        'concerns': info['concerns'],
                        'categories': info['categories'],
                        'found_in': info['found_in']
                    }
        return {'is_harmful': False}

    def _word_boundary_match(self, ingredient):
        words = ingredient.split()
        for harmful_name, info in self.harmful_ingredients.items():
            if harmful_name in words:
                return {
                    'is_harmful': True,
                    'matched_name': harmful_name,
                    'score': info['score'],
                    'concerns': info['concerns'],
                    'categories': info['categories'],
                    'found_in': info['found_in']
                }
        return {'is_harmful': False}

    def _calculate_safety_score(self, harmful_ingredients, total_ingredients):
        if total_ingredients == 0:
            return 0
        
        base_score = 100
        category_weights = {
            'carcinogen': 15,
            'developmental_toxin': 12,
            'neurotoxin': 12,
            'endocrine_disruptor': 10,
            'organ_toxin': 10,
            'respiratory_toxin': 8,
            'allergen': 6,
            'irritant': 5,
            'environmental_toxin': 5,
            'bioaccumulative': 8,
            'skin_penetrator': 6,
            'photosensitizer': 5
        }
        
        for ingredient in harmful_ingredients:
            # Base deduction from ingredient score
            base_score -= ingredient['score']
            
            # Additional deductions based on categories and their weights
            for category in ingredient['categories']:
                if category in category_weights:
                    base_score -= category_weights[category]
            
            # Extra deduction for multiple harmful categories
            if len(ingredient['categories']) > 2:
                base_score -= (len(ingredient['categories']) - 2) * 3
        
        # Adjust for total number of ingredients (more ingredients = higher risk)
        if total_ingredients > 15:
            base_score -= (total_ingredients - 15) * 0.5
        
        return max(0, min(100, base_score))  # Ensure score is between 0 and 100

    def _get_recommendations(self, harmful_ingredients):
        recommendations = []
        
        for harmful in harmful_ingredients:
            ingredient_name = harmful['matched_name']
            if ingredient_name in self.safe_alternatives:
                recommendations.append({
                    'harmful_ingredient': ingredient_name,
                    'safer_alternatives': self.safe_alternatives[ingredient_name]['alternatives'],
                    'explanation': self.safe_alternatives[ingredient_name]['explanation'],
                    'product_types': harmful['found_in']
                })
        
        # Add general safety tips based on categories found
        general_tips = self._generate_safety_tips(harmful_ingredients)
        
        return {
            'specific_alternatives': recommendations,
            'general_tips': general_tips
        }

    def _generate_safety_tips(self, harmful_ingredients):
        tips = []
        categories_found = set()
        
        for ingredient in harmful_ingredients:
            categories_found.update(ingredient['categories'])
        
        if 'carcinogen' in categories_found:
            tips.append("Look for products certified by clean beauty standards organizations")
        
        if 'endocrine_disruptor' in categories_found:
            tips.append("Choose products with minimal ingredients and clear labeling")
        
        if 'allergen' in categories_found:
            tips.append("Patch test new products and choose fragrance-free options")
        
        if 'environmental_toxin' in categories_found:
            tips.append("Consider reef-safe and biodegradable products")
        
        # Add general tips
        tips.extend([
            "Research brands that focus on natural and organic ingredients",
            "Check for third-party certifications for safety claims",
            "Consider making simple products at home with natural ingredients",
            "Use the EWG's Skin Deep database for detailed ingredient research"
        ])
        
        return tips 

    def clean_ingredients(self, text):
        """Enhanced ingredient cleaning and parsing."""
        # Remove common unnecessary text
        text = re.sub(r'\([^)]*\)', ' ', text)  # Remove content in parentheses
        text = re.sub(r'\b(may contain|contains|ingredients|ingrédients|composition)\b', ' ', text, flags=re.IGNORECASE)
        
        # Replace various separators with commas
        text = re.sub(r'[;|•|\n|/]', ',', text)
        
        # Split by comma and clean each ingredient
        ingredients = []
        for ingredient in text.split(','):
            ingredient = ingredient.strip()
            if ingredient and len(ingredient) > 1:
                # Remove percentage numbers
                ingredient = re.sub(r'\d+(\.\d+)?%', '', ingredient)
                # Remove special characters but keep hyphens and periods
                ingredient = re.sub(r'[^\w\s\-\.]', ' ', ingredient)
                # Remove extra spaces
                ingredient = ' '.join(ingredient.split())
                # Remove common prefixes/suffixes
                ingredient = re.sub(r'^(and|or|with|contains)\s+', '', ingredient, flags=re.IGNORECASE)
                if ingredient:
                    ingredients.append(ingredient)
        
        # Remove duplicates while preserving order
        seen = set()
        ingredients = [x for x in ingredients if not (x.lower() in seen or seen.add(x.lower()))]
        
        print(f"Found {len(ingredients)} unique ingredients: {ingredients}")  # Debug log
        return ingredients 