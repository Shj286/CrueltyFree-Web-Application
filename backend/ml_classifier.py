from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import numpy as np
import joblib
import os
import json
import re

class IngredientMLClassifier:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 5),
            max_features=10000,
            lowercase=True,
            strip_accents='unicode'
        )
        self.classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=30,
            min_samples_split=2,
            random_state=42,
            class_weight='balanced'
        )
        self.model_path = os.path.join(os.path.dirname(__file__), 'models')
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
            
    def _normalize_ingredient(self, text):
        """Normalize ingredient text for better matching."""
        text = text.lower().strip()
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
            
    def prepare_data(self):
        """Prepare training data from the toxic chemicals database."""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            database_path = os.path.join(current_dir, 'toxic_chemicals_database.json')
            
            with open(database_path, 'r') as f:
                data = json.load(f)
                harmful_ingredients = data.get('harmful_ingredients', {})
            
            X = []  # Ingredient names
            y = []  # Labels and scores
            
            # Add harmful ingredients with variations
            for name, info in harmful_ingredients.items():
                # Add main name
                normalized_name = self._normalize_ingredient(name)
                if normalized_name:
                    X.append(normalized_name)
                    y.append({
                        'is_harmful': 1,
                        'score': info.get('score', 5),
                        'categories': info.get('categories', [])
                    })
                
                # Add alternative names
                for alt_name in info.get('alternative_names', []):
                    normalized_alt = self._normalize_ingredient(alt_name)
                    if normalized_alt and normalized_alt not in X:
                        X.append(normalized_alt)
                        y.append({
                            'is_harmful': 1,
                            'score': info.get('score', 5),
                            'categories': info.get('categories', [])
                        })
                        
                # Add common variations
                variations = self._generate_variations(normalized_name)
                for var in variations:
                    if var not in X:
                        X.append(var)
                        y.append({
                            'is_harmful': 1,
                            'score': info.get('score', 5),
                            'categories': info.get('categories', [])
                        })
            
            return X, y
        except Exception as e:
            print(f"Error preparing data: {e}")
            return [], []
            
    def _generate_variations(self, name):
        """Generate common variations of ingredient names."""
        variations = set()
        # Remove spaces
        variations.add(name.replace(' ', ''))
        # Replace hyphens with spaces and vice versa
        variations.add(name.replace('-', ' '))
        variations.add(name.replace(' ', '-'))
        return variations
            
    def train(self):
        """Train the ML model on the ingredient data."""
        X, y = self.prepare_data()
        if not X or not y:
            return False
            
        # Convert text to features
        X_features = self.vectorizer.fit_transform(X)
        
        # Extract labels for harmful/safe classification
        y_harmful = np.array([label['is_harmful'] for label in y])
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_features, y_harmful, test_size=0.2, random_state=42
        )
        
        # Train model
        self.classifier.fit(X_train, y_train)
        
        # Save models
        joblib.dump(self.vectorizer, os.path.join(self.model_path, 'vectorizer.joblib'))
        joblib.dump(self.classifier, os.path.join(self.model_path, 'classifier.joblib'))
        
        # Calculate accuracy
        accuracy = self.classifier.score(X_test, y_test)
        print(f"Model accuracy: {accuracy * 100:.2f}%")
        
        return True
        
    def load_models(self):
        """Load trained models."""
        try:
            self.vectorizer = joblib.load(os.path.join(self.model_path, 'vectorizer.joblib'))
            self.classifier = joblib.load(os.path.join(self.model_path, 'classifier.joblib'))
            return True
        except:
            return False
            
    def predict(self, ingredient):
        """Predict if an ingredient is harmful."""
        try:
            # Normalize input
            normalized_ingredient = self._normalize_ingredient(ingredient)
            if not normalized_ingredient:
                return None
                
            # Transform ingredient text
            X = self.vectorizer.transform([normalized_ingredient])
            
            # Get prediction and probability
            prediction = self.classifier.predict(X)[0]
            probability = self.classifier.predict_proba(X)[0]
            
            # Higher confidence threshold for positive predictions
            confidence = float(max(probability))
            is_harmful = bool(prediction) and confidence > 0.65
            
            return {
                'is_harmful': is_harmful,
                'confidence': confidence,
                'ingredient': ingredient,
                'normalized_form': normalized_ingredient
            }
        except Exception as e:
            print(f"Error in prediction: {e}")
            return None 