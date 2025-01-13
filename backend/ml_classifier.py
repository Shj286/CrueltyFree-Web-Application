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
    def __init__(self):
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
        """Enhanced ingredient normalization with chemical name preservation."""
        text = text.lower().strip()
        
        # Preserve chemical numbers and formulas
        chemical_numbers = re.findall(r'[a-z]+\d+', text)
        chemical_formulas = re.findall(r'\([^)]*\)', text)
        
        # Remove parentheses and their contents unless they contain chemical formulas
        text = re.sub(r'\([^)]*\)', lambda m: m.group() if any(f in m.group().lower() for f in chemical_formulas) else '', text)
        
        # Remove percentages
        text = re.sub(r'\d+(\.\d+)?%', '', text)
        
        # Standardize separators
        text = re.sub(r'[-/,]', ' ', text)
        
        # Remove special characters but preserve chemical symbols
        text = ''.join(c for c in text if c.isalnum() or c.isspace() or c in '-')
        
        # Normalize spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
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
        """Make predictions with category-specific thresholds."""
        try:
            # Normalize input
            normalized_ingredient = self._normalize_ingredient(ingredient)
            if not normalized_ingredient:
                return None
                
            # Generate variations
            variations = [
                normalized_ingredient,
                normalized_ingredient.replace(' ', ''),
                normalized_ingredient.replace(' ', '-')
            ]
            
            predictions = []
            confidences = []
            chemical_features = []
            
            # Predict for each variation
            for var in variations:
                if var:
                    # Extract features
                    features = self._extract_chemical_features(var)
                    chemical_features.append(features)
                    
                    # Get TF-IDF features
                    X_tfidf = self.vectorizer.transform([var])
                    
                    # Get chemical features
                    X_additional = np.array([list(features.values())])
                    
                    # Combine features
                    X_combined = np.hstack((X_tfidf.toarray(), X_additional))
                    
                    # Make prediction
                    pred = self.classifier.predict(X_combined)[0]
                    prob = self.classifier.predict_proba(X_combined)[0]
                    max_prob = max(prob)
                    
                    predictions.append(pred)
                    confidences.append(max_prob)
            
            # Calculate chemical score and determine category
            avg_chemical_score = np.mean([sum(f.values()) for f in chemical_features])
            primary_category = self._get_ingredient_category(chemical_features[0])
            
            # Get category-specific thresholds
            thresholds = self.category_thresholds.get(primary_category, self.category_thresholds['default'])
            
            # Weight predictions by confidence
            weighted_pred = np.average(predictions, weights=confidences)
            avg_confidence = np.mean(confidences)
            max_confidence = max(confidences)
            
            # Make final decision using category-specific thresholds
            is_harmful = (weighted_pred > thresholds['base'] and 
                        (avg_confidence > thresholds['confidence'] or 
                         max_confidence > 0.8 or
                         (avg_chemical_score > 2 and avg_confidence > 0.6)))
            
            return {
                'is_harmful': bool(is_harmful),
                'confidence': float(avg_confidence),
                'max_confidence': float(max_confidence),
                'ingredient': ingredient,
                'normalized_form': normalized_ingredient,
                'variations_checked': len(variations),
                'chemical_score': float(avg_chemical_score),
                'category': primary_category,
                'is_chemical': avg_chemical_score > 0
            }
        except Exception as e:
            print(f"Error in prediction: {e}")
            return None 