import json
import re
from difflib import SequenceMatcher
import os

class IngredientAnalyzer:
    def __init__(self):
        self.load_database()

    def load_database(self):
        try:
            # Get the absolute path to the database file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            database_path = os.path.join(current_dir, 'toxic_chemicals_database.json')
            
            print(f"Loading database from: {database_path}")
            
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
        """Enhanced ingredient checking with improved matching accuracy."""
        ingredient_lower = ingredient.lower().strip()
        print(f"\nChecking ingredient: {ingredient}")
        
        # Step 1: Normalize the ingredient name
        normalized = self._normalize_ingredient_name(ingredient_lower)
        print(f"Normalized form: {normalized}")
        
        # Step 2: Check exact matches first (including alternative names)
        exact_match = self._check_exact_matches(normalized, ingredient_lower)
        if exact_match:
            return exact_match
        
        # Step 3: Check for chemical variations and derivatives
        chemical_match = self._check_chemical_variations(normalized, ingredient_lower)
        if chemical_match:
            return chemical_match
        
        # Step 4: Check for compound matches
        compound_match = self._check_compound_ingredient(normalized, ingredient_lower)
        if compound_match:
            return compound_match
        
        # Step 5: Check for partial matches with high confidence
        partial_match = self._check_partial_matches(normalized, ingredient_lower)
        if partial_match:
            return partial_match
            
        print(f"No harmful match found for: {ingredient}")
        return {
            'is_harmful': False,
            'matched_name': None,
            'score': 0,
            'concerns': [],
            'categories': [],
            'found_in': []
        }

    def _normalize_ingredient_name(self, name):
        """Enhanced ingredient name normalization."""
        # Remove common prefixes/suffixes
        name = re.sub(r'^(and|or|contains|with|derived from|from)\s+', '', name)
        
        # Remove parentheses and their contents (but keep chemical info)
        name = re.sub(r'\([^)]*?(color|colour|ci|no\.|grade)\s*[^)]*\)', '', name, flags=re.IGNORECASE)
        
        # Remove numbers but keep chemical numbers
        name = re.sub(r'(?<!\b[A-Za-z])\d+(?!\b[A-Za-z])', '', name)
        
        # Convert to lowercase and remove special characters but keep hyphens and dots
        name = re.sub(r'[^a-z0-9\-\.]', '', name.lower())
        
        # Remove common chemical suffixes but keep important ones
        name = re.sub(r'(acid|ester|salt|oxide|hydroxide|sulfate|acetate)$', '', name)
        
        # Remove common filler words
        name = re.sub(r'\b(powder|extract|oil|solution|derivative|compound|certified|organic|natural)\b', '', name)
        
        return name.strip()

    def _check_exact_matches(self, normalized, original):
        """Check for exact matches including alternative names."""
        for harmful_name, info in self.harmful_ingredients.items():
            harmful_normalized = self._normalize_ingredient_name(harmful_name)
            
            # Direct match check
            if normalized == harmful_normalized:
                print(f"Found exact match: {original} -> {harmful_name}")
                return self._create_harmful_result(harmful_name, info)
            
            # Check alternative names
            for alt_name in info.get('alternative_names', []):
                alt_normalized = self._normalize_ingredient_name(alt_name)
                if normalized == alt_normalized:
                    print(f"Found alternative name match: {original} -> {harmful_name}")
                    return self._create_harmful_result(harmful_name, info)
        return None

    def _check_chemical_variations(self, normalized, original):
        """Enhanced chemical variation checking."""
        chemical_patterns = {
            r'methyl': ['paraben', 'siloxane', 'isothiazolinone', 'ether', 'ester'],
            r'ethyl': ['paraben', 'phthalate', 'silicate', 'ether', 'ester'],
            r'propyl': ['paraben', 'phthalate', 'alcohol', 'ester'],
            r'butyl': ['paraben', 'phthalate', 'alcohol', 'ester'],
            r'benzyl': ['alcohol', 'salicylate', 'benzoate', 'paraben'],
            r'phenyl': ['acetate', 'salicylate', 'mercuric', 'paraben'],
            r'sodium': ['lauryl', 'laureth', 'benzoate', 'chloride'],
            r'potassium': ['sorbate', 'benzoate', 'chloride'],
            r'calcium': ['carbonate', 'phosphate', 'chloride'],
            r'zinc': ['oxide', 'pyrithione', 'stearate'],
            r'titanium': ['dioxide', 'oxide'],
            r'aluminum': ['chloride', 'hydroxide', 'oxide', 'stearate']
        }
        
        for prefix, suffixes in chemical_patterns.items():
            if prefix in normalized:
                for suffix in suffixes:
                    if suffix in normalized:
                        # Search for matching harmful ingredients with higher accuracy
                        for harmful_name, info in self.harmful_ingredients.items():
                            harmful_lower = harmful_name.lower()
                            if (prefix in harmful_lower and suffix in harmful_lower) or \
                               any(prefix in alt.lower() and suffix in alt.lower() 
                                   for alt in info.get('alternative_names', [])):
                                confidence = self._calculate_chemical_match_confidence(
                                    normalized, harmful_lower, prefix, suffix)
                                if confidence >= 0.85:  # High confidence threshold
                                    print(f"Found chemical variation match: {original} -> {harmful_name}")
                                    return self._create_harmful_result(harmful_name, info)
        return None

    def _calculate_chemical_match_confidence(self, str1, str2, prefix, suffix):
        """Calculate confidence score for chemical matches."""
        # Base similarity
        base_similarity = SequenceMatcher(None, str1, str2).ratio()
        
        # Position similarity (prefix and suffix should be in similar positions)
        pos_similarity = 1.0
        pos1_prefix = str1.find(prefix)
        pos2_prefix = str2.find(prefix)
        if abs(pos1_prefix - pos2_prefix) > 3:  # Allow small position differences
            pos_similarity *= 0.8
            
        pos1_suffix = str1.find(suffix)
        pos2_suffix = str2.find(suffix)
        if abs(pos1_suffix - pos2_suffix) > 3:
            pos_similarity *= 0.8
        
        # Length similarity
        len_similarity = 1 - (abs(len(str1) - len(str2)) / max(len(str1), len(str2)))
        
        # Combined score with weights
        confidence = (base_similarity * 0.4 + 
                     pos_similarity * 0.4 + 
                     len_similarity * 0.2)
        
        return confidence

    def _check_compound_ingredient(self, normalized, original):
        """Enhanced compound ingredient checking."""
        # Check for compound ingredients with multiple parts
        for harmful_name, info in self.harmful_ingredients.items():
            harmful_parts = set(self._normalize_ingredient_name(harmful_name).split('-'))
            
            # Check if all parts of the harmful ingredient are in the normalized name
            if len(harmful_parts) > 1 and all(part in normalized for part in harmful_parts):
                print(f"Found compound match: {original} -> {harmful_name}")
                return self._create_harmful_result(harmful_name, info)
            
            # Check compound alternative names
            for alt_name in info.get('alternative_names', []):
                alt_parts = set(self._normalize_ingredient_name(alt_name).split('-'))
                if len(alt_parts) > 1 and all(part in normalized for part in alt_parts):
                    print(f"Found compound alternative match: {original} -> {harmful_name}")
                    return self._create_harmful_result(harmful_name, info)
                
            # Check for chemical family matches
            if any(family in normalized for family in ['phthalate', 'paraben', 'siloxane', 'glycol']):
                if any(family in harmful_name.lower() for family in ['phthalate', 'paraben', 'siloxane', 'glycol']):
                    chemical_match_score = self._calculate_chemical_match_score(normalized, harmful_name)
                    if chemical_match_score >= 0.8:  # High confidence threshold
                        print(f"Found chemical family match: {original} -> {harmful_name}")
                        return self._create_harmful_result(harmful_name, info)
        
        return None

    def _check_partial_matches(self, normalized, original):
        """Enhanced partial matching with improved accuracy."""
        best_match = None
        highest_confidence = 0.75  # Minimum confidence threshold
        
        for harmful_name, info in self.harmful_ingredients.items():
            harmful_normalized = self._normalize_ingredient_name(harmful_name)
            
            # Calculate match confidence
            confidence = self._calculate_match_confidence(normalized, harmful_normalized)
            
            if confidence > highest_confidence:
                highest_confidence = confidence
                best_match = (harmful_name, info)
                
            # Check alternative names
            for alt_name in info.get('alternative_names', []):
                alt_normalized = self._normalize_ingredient_name(alt_name)
                confidence = self._calculate_match_confidence(normalized, alt_normalized)
                
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = (harmful_name, info)
        
        if best_match:
            print(f"Found partial match with {highest_confidence:.2f} confidence: {original} -> {best_match[0]}")
            return self._create_harmful_result(best_match[0], best_match[1])
            
        return None

    def _calculate_match_confidence(self, str1, str2):
        """Calculate the confidence score for partial matches."""
        # Length difference penalty
        length_diff = abs(len(str1) - len(str2)) / max(len(str1), len(str2))
        length_score = 1 - length_diff
        
        # Sequence matcher similarity
        sequence_score = SequenceMatcher(None, str1, str2).ratio()
        
        # Common substring score
        common_substrings = self._find_common_substrings(str1, str2)
        substring_score = sum(len(s) for s in common_substrings) / max(len(str1), len(str2))
        
        # Chemical pattern score
        chemical_score = self._calculate_chemical_match_score(str1, str2)
        
        # Weighted average of all scores
        confidence = (
            length_score * 0.2 +
            sequence_score * 0.3 +
            substring_score * 0.2 +
            chemical_score * 0.3
        )
        
        return confidence

    def _calculate_chemical_match_score(self, str1, str2):
        """Calculate similarity score based on chemical patterns."""
        chemical_patterns = [
            r'methyl', r'ethyl', r'propyl', r'butyl',
            r'benzyl', r'phenyl', r'sodium', r'potassium',
            r'calcium', r'zinc', r'aluminum', r'titanium',
            r'oxide', r'chloride', r'sulfate', r'phosphate',
            r'acetate', r'benzoate', r'salicylate', r'paraben',
            r'phthalate', r'siloxane', r'glycol'
        ]
        
        # Count matching patterns
        matches = sum(1 for pattern in chemical_patterns 
                     if re.search(pattern, str1) and re.search(pattern, str2))
        
        # Calculate score based on matches
        if matches == 0:
            return 0
        return min(1.0, matches * 0.25)  # Cap at 1.0

    def _find_common_substrings(self, str1, str2):
        """Find all common substrings between two strings."""
        common = []
        len1, len2 = len(str1), len(str2)
        
        # Create a matrix of matches
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        longest = 0
        
        # Fill the matrix
        for i in range(len1):
            for j in range(len2):
                if str1[i] == str2[j]:
                    matrix[i + 1][j + 1] = matrix[i][j] + 1
                    if matrix[i + 1][j + 1] > longest:
                        longest = matrix[i + 1][j + 1]
        
        # Extract common substrings
        for length in range(longest, 2, -1):  # Only consider substrings of length > 2
            for i in range(len1 + 1):
                for j in range(len2 + 1):
                    if matrix[i][j] == length:
                        common.append(str1[i - length:i])
        
        return common

    def _create_harmful_result(self, harmful_name, info):
        """Create a standardized harmful ingredient result."""
        return {
            'is_harmful': True,
            'matched_name': harmful_name,
            'score': info.get('score', 5),
            'concerns': info.get('concerns', []),
            'categories': info.get('categories', []),
            'found_in': info.get('found_in', [])
        }

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

class EWGScraper:
    def __init__(self):
        self.ingredients_data = {}

    def get_all_ingredients(self):
        # TODO: Implement actual EWG scraping
        return self.ingredients_data 