from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import precision_recall_fscore_support, classification_report
from sklearn.preprocessing import StandardScaler
import numpy as np
import joblib
import os
import json
import re

class IngredientMLClassifier:
    def __init__(self, harmful_ingredients=None, safe_alternatives=None):
        self.harmful_ingredients = harmful_ingredients or {}
        self.safe_alternatives = safe_alternatives or {}
        
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 7),
            max_features=12000,
            lowercase=True,
            strip_accents='unicode',
            min_df=2,
            max_df=0.95
        )
        
        self.base_classifier = RandomForestClassifier(
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'
        )
        
        self.param_grid = {
            'n_estimators': [250, 300],
            'max_depth': [35, 40],
            'min_samples_split': [2, 3],
            'min_samples_leaf': [1, 2],
            'max_features': ['sqrt', 'log2']
        }
        
        self.model_path = os.path.join(os.path.dirname(__file__), 'models')
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            
        # Enhanced chemical patterns with specific categories
        self.chemical_patterns = {
            # Parabens and preservatives
            'paraben': r'paraben$',
            'preservative': r'(phenoxyethanol|benzoate|sorbate|methylisothiazolinone)',
            
            # Phthalates and plasticizers
            'phthalate': r'phthalate$',
            'plasticizer': r'(adipate|sebacate|citrate|acetate)',
            
            # Sulfates and surfactants
            'sulfate': r'sulfate$|sulphate$',
            'surfactant': r'(lauryl|laureth|cetyl|stearyl|cetearyl)',
            
            # Formaldehyde and derivatives
            'formaldehyde': r'formaldehyde|formalin',
            'formaldehyde_donor': r'(quaternium|diazolidinyl|imidazolidinyl|dmhf|dmdm)',
            
            # Heavy metals and compounds
            'heavy_metal': r'(mercury|lead|cadmium|arsenic|antimony)',
            'metal_compound': r'(acetate|oxide|chloride|sulfide|nitrate)',
            
            # Antimicrobials and antibacterials
            'antimicrobial': r'(triclosan|triclocarban|chloroxylenol|benzalkonium)',
            'antibacterial': r'(chlorhexidine|hexachlorophene|irgasan)',
            
            # Other harmful categories
            'solvent': r'(toluene|xylene|benzene|acetone)',
            'ethanolamine': r'(diethanolamine|triethanolamine|monoethanolamine)',
            'uv_filter': r'(benzophenone|oxybenzone|avobenzone|octinoxate)',
            
            # Chemical structure indicators
            'chemical_prefix': r'^(mono|di|tri|tetra|penta|hexa|methyl|ethyl|propyl|butyl)',
            'chemical_suffix': r'(oxide|chloride|bromide|iodide|hydroxide|carbonate)$',
            
            # Natural and safe indicators
            'natural': r'(oil|butter|extract|vera|flower|leaf|root|seed|fruit)',
            'vitamin': r'(vitamin|tocopherol|retinol|niacinamide|panthenol)',
            'protein': r'(collagen|keratin|peptide|protein|amino)',
            'mineral': r'(mica|kaolin|zinc|titanium|iron)',
            
            # Additional chemical properties
            'acid': r'acid$',
            'alcohol': r'alcohol$',
            'amine': r'amine$',
            'ester': r'(acetate|propionate|stearate|palmitate)',
            'number': r'\d+'
        }
        
        # Category-specific confidence thresholds
        self.category_thresholds = {
            'antimicrobial': {'base': 0.5, 'confidence': 0.6},
            'heavy_metal': {'base': 0.5, 'confidence': 0.6},
            'formaldehyde': {'base': 0.5, 'confidence': 0.6},
            'paraben': {'base': 0.6, 'confidence': 0.7},
            'phthalate': {'base': 0.6, 'confidence': 0.7},
            'sulfate': {'base': 0.6, 'confidence': 0.7},
            'default': {'base': 0.65, 'confidence': 0.75}
        }
            
    def _normalize_ingredient(self, text):
        """Enhanced ingredient normalization with better chemical name handling."""
        try:
            text = text.lower().strip()
            
            # Preserve chemical numbers and formulas
            chemical_numbers = re.findall(r'[a-z]+\d+', text)
            chemical_formulas = re.findall(r'\([^)]*\)', text)
            
            # Common chemical name variations
            variations = {
                'oxide': ['oxide', 'oxides', 'oxidum'],
                'zinc': ['zinc', 'zn', 'zinc oxide', 'zno'],
                'titanium': ['titanium', 'ti', 'titanium dioxide', 'tio2'],
                'paraben': ['paraben', 'parabin', 'parabean'],
                'sulfate': ['sulfate', 'sulphate', 'sulfates', 'sulphates']
            }
            
            # Normalize common variations
            for base, vars in variations.items():
                for var in vars:
                    if var in text:
                        text = text.replace(var, base)
            
            # Remove percentages and unnecessary words
            text = re.sub(r'\d+(\.\d+)?%', '', text)
            text = re.sub(r'\b(pure|natural|organic|synthetic)\b', '', text)
            
            # Standardize separators
            text = re.sub(r'[-/,]', ' ', text)
            
            # Clean up but preserve chemical formulas
            text = ' '.join(word for word in text.split() if word)
            
            return text.strip()
        except Exception as e:
            print(f"Error in normalization: {e}")
            return text
    
    def _extract_chemical_features(self, text):
        """Extract chemical features with pattern matching."""
        features = {}
        for name, pattern in self.chemical_patterns.items():
            features[f'has_{name}'] = 1 if re.search(pattern, text.lower()) else 0
        return features
    
    def _get_ingredient_category(self, features):
        """Determine the primary category of an ingredient based on its features."""
        category_scores = {
            'antimicrobial': features.get('has_antimicrobial', 0) + features.get('has_antibacterial', 0),
            'heavy_metal': features.get('has_heavy_metal', 0) + features.get('has_metal_compound', 0),
            'formaldehyde': features.get('has_formaldehyde', 0) + features.get('has_formaldehyde_donor', 0),
            'paraben': features.get('has_paraben', 0),
            'phthalate': features.get('has_phthalate', 0),
            'sulfate': features.get('has_sulfate', 0)
        }
        
        max_score = max(category_scores.values())
        if max_score > 0:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        return 'default'
            
    def prepare_data(self):
        """Prepare training data with enhanced feature generation."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            database_path = os.path.join(current_dir, 'toxic_chemicals_database.json')
            
            with open(database_path, 'r') as f:
                data = json.load(f)
                harmful_ingredients = data.get('harmful_ingredients', {})
            
            X = []  # Ingredient names
            y = []  # Labels
            additional_features = []  # Chemical features
            
            # Process harmful ingredients
            for name, info in harmful_ingredients.items():
                normalized_name = self._normalize_ingredient(name)
                if normalized_name:
                    X.append(normalized_name)
                    y.append(1)
                    additional_features.append(self._extract_chemical_features(normalized_name))
                    
                    # Add variations
                    variations = [
                        normalized_name.replace(' ', ''),
                        normalized_name.replace(' ', '-')
                    ]
                    
                    # Add alternative names
                    if 'alternative_names' in info:
                        variations.extend([self._normalize_ingredient(alt) for alt in info['alternative_names']])
                    
                    for var in variations:
                        if var and var != normalized_name:
                            X.append(var)
                            y.append(1)
                            additional_features.append(self._extract_chemical_features(var))
            
            # Add safe ingredients with expanded list
            safe_ingredients = [
                "water", "aqua", "glycerin", "aloe vera", "vitamin e",
                "panthenol", "allantoin", "glycine", "arginine", "olive oil",
                "jojoba oil", "shea butter", "coconut oil", "almond oil",
                "hyaluronic acid", "niacinamide", "tocopherol", "xanthan gum",
                "citric acid", "potassium sorbate", "sodium benzoate",
                "camellia sinensis leaf extract", "chamomilla recutita extract",
                "rosa damascena flower water", "lavandula angustifolia oil",
                "squalane", "beta glucan", "ceramide", "peptide",
                "sodium hyaluronate", "green tea extract", "centella asiatica",
                "panthenol", "bisabolol", "allantoin", "madecassoside"
            ]
            
            for ingredient in safe_ingredients:
                normalized = self._normalize_ingredient(ingredient)
                if normalized:
                    X.append(normalized)
                    y.append(0)
                    additional_features.append(self._extract_chemical_features(normalized))
            
            return X, y, additional_features
        except Exception as e:
            print(f"Error preparing data: {e}")
            return [], [], []
            
    def train(self):
        """Train model with enhanced feature engineering and grid search."""
        X_text, y, additional_features = self.prepare_data()
        if not X_text or not y:
            return False
            
        # Convert text to TF-IDF features
        X_tfidf = self.vectorizer.fit_transform(X_text)
        
        # Convert additional features to array and scale them
        X_additional = np.array([list(f.values()) for f in additional_features])
        scaler = StandardScaler()
        X_additional_scaled = scaler.fit_transform(X_additional)
        
        # Combine TF-IDF and additional features
        X_combined = np.hstack((X_tfidf.toarray(), X_additional_scaled))
        y = np.array(y)
        
        # Perform grid search
        grid_search = GridSearchCV(
            self.base_classifier,
            self.param_grid,
            cv=5,
            scoring='f1',
            n_jobs=-1
        )
        
        # Split data for final evaluation
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train with grid search
        grid_search.fit(X_train, y_train)
        self.classifier = grid_search.best_estimator_
        
        # Print best parameters
        print("\nBest parameters:", grid_search.best_params_)
        print("Best cross-validation score:", grid_search.best_score_)
        
        # Evaluate on test set
        y_pred = self.classifier.predict(X_test)
        
        # Print detailed classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred, target_names=['Safe', 'Harmful']))
        
        # Save models
        joblib.dump(self.vectorizer, os.path.join(self.model_path, 'vectorizer.joblib'))
        joblib.dump(self.classifier, os.path.join(self.model_path, 'classifier.joblib'))
        joblib.dump(scaler, os.path.join(self.model_path, 'scaler.joblib'))
        
        return True
        
    def predict(self, ingredient):
        """Enhanced prediction with better accuracy and safety checks."""
        try:
            normalized = self._normalize_ingredient(ingredient)
            if not normalized or len(normalized) <= 1:
                return None

            # Known safe ingredient patterns
            safe_patterns = [
                r'\b(vitamin|mineral)\s+[a-e]\d*\b',  # Vitamins and minerals
                r'\b(aloe|jojoba|shea|coconut|argan)\b',  # Natural oils and extracts
                r'\b(glycerin|panthenol|allantoin|hyaluronic acid)\b',  # Safe synthetics
                r'\b(niacinamide|tocopherol|ceramide)\b'  # Beneficial ingredients
            ]
            
            # Check for safe patterns first
            for pattern in safe_patterns:
                if re.search(pattern, normalized, re.IGNORECASE):
                    return {
                        'is_harmful': False,
                        'confidence': 1.0,
                        'ingredient': ingredient,
                        'category': 'safe ingredients',
                        'chemical_score': 0
                    }

            # Check database for known harmful ingredients
            compound_matches = []
            for harmful in self.harmful_ingredients.keys():
                if harmful in normalized or normalized in harmful:
                    compound_matches.append(harmful)

            # If found in harmful ingredients database
            if compound_matches:
                highest_score = 0
                matched_ingredient = None
                
                for match in compound_matches:
                    info = self.harmful_ingredients[match]
                    if info['score'] > highest_score:
                        highest_score = info['score']
                        matched_ingredient = match

                if matched_ingredient and highest_score >= 7:  # Only if score is high enough
                    return {
                        'is_harmful': True,
                        'confidence': 1.0,
                        'ingredient': ingredient,
                        'matched_name': matched_ingredient,
                        'category': self.harmful_ingredients[matched_ingredient]['categories'][0],
                        'chemical_score': highest_score,
                        'concerns': self.harmful_ingredients[matched_ingredient]['concerns']
                    }

            # ML-based prediction for unknown ingredients
            features = self._extract_chemical_features(normalized)
            
            # Calculate chemical risk score
            risk_score = 0
            risk_score += features.get('has_paraben', 0) * 3
            risk_score += features.get('has_phthalate', 0) * 3
            risk_score += features.get('has_formaldehyde', 0) * 4
            risk_score += features.get('has_heavy_metal', 0) * 4
            risk_score += features.get('has_solvent', 0) * 2
            risk_score -= features.get('has_natural', 0) * 2
            risk_score -= features.get('has_vitamin', 0) * 2
            
            # Get ML prediction
            X_tfidf = self.vectorizer.transform([normalized])
            X_additional = np.array([list(features.values())])
            X_combined = np.hstack((X_tfidf.toarray(), X_additional))
            
            pred = self.classifier.predict(X_combined)[0]
            prob = self.classifier.predict_proba(X_combined)[0]
            confidence = float(max(prob))

            # More conservative approach to harmful classification
            is_harmful = (pred == 1 and confidence > 0.8) or risk_score >= 3

            return {
                'is_harmful': is_harmful,
                'confidence': confidence,
                'ingredient': ingredient,
                'category': self._get_ingredient_category(features),
                'chemical_score': risk_score,
                'is_chemical': bool(features.get('has_chemical_suffix', 0) or 
                                  features.get('has_chemical_prefix', 0))
            }

        except Exception as e:
            print(f"Error in prediction: {e}")
            return None

    def get_ingredient_category(self, ingredient):
        """Get the category of an ingredient based on chemical features."""
        try:
            # Normalize the ingredient name
            normalized = self._normalize_ingredient(ingredient)
            
            # Extract chemical features
            features = self._extract_chemical_features(normalized)
            
            # Determine primary category based on features
            category_scores = {
                'paraben': features.get('has_paraben', 0),
                'sulfate': features.get('has_sulfate', 0),
                'phthalate': features.get('has_phthalate', 0),
                'formaldehyde': features.get('has_formaldehyde', 0),
                'preservative': features.get('has_preservative', 0),
                'antimicrobial': features.get('has_antimicrobial', 0),
                'heavy_metal': features.get('has_heavy_metal', 0)
            }
            
            # Get the category with highest score
            max_score = max(category_scores.values())
            if max_score > 0:
                return max(category_scores.items(), key=lambda x: x[1])[0]
            
            # If no specific category is found, check for general chemical properties
            if features.get('has_chemical_suffix', 0) or features.get('has_chemical_prefix', 0):
                return 'chemical'
            
            # Default category for natural ingredients
            if features.get('has_natural', 0):
                return 'natural'
            
            return 'general'
            
        except Exception as e:
            print(f"Error determining category for {ingredient}: {e}")
            return 'general' 