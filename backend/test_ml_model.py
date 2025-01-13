from ml_classifier import IngredientMLClassifier
from tabulate import tabulate
from collections import defaultdict

def test_model():
    # Initialize the classifier
    classifier = IngredientMLClassifier()
    
    # Train the model
    print("Training model...")
    success = classifier.train()
    
    if not success:
        print("Failed to train model")
        return
        
    # Expanded test cases with categorization
    test_cases = [
        # Known harmful ingredients - Parabens
        {"ingredient": "methylparaben", "expected": True, "category": "Paraben"},
        {"ingredient": "propylparaben", "expected": True, "category": "Paraben"},
        {"ingredient": "butylparaben", "expected": True, "category": "Paraben"},
        {"ingredient": "ethylparaben", "expected": True, "category": "Paraben"},
        {"ingredient": "isobutylparaben", "expected": True, "category": "Paraben"},
        
        # Known harmful ingredients - Formaldehyde and derivatives
        {"ingredient": "formaldehyde", "expected": True, "category": "Formaldehyde"},
        {"ingredient": "quaternium-15", "expected": True, "category": "Formaldehyde"},
        {"ingredient": "diazolidinyl urea", "expected": True, "category": "Formaldehyde"},
        {"ingredient": "imidazolidinyl urea", "expected": True, "category": "Formaldehyde"},
        
        # Known harmful ingredients - Sulfates
        {"ingredient": "sodium lauryl sulfate", "expected": True, "category": "Sulfate"},
        {"ingredient": "sodium laureth sulfate", "expected": True, "category": "Sulfate"},
        {"ingredient": "ammonium lauryl sulfate", "expected": True, "category": "Sulfate"},
        
        # Known harmful ingredients - Phthalates
        {"ingredient": "dibutyl phthalate", "expected": True, "category": "Phthalate"},
        {"ingredient": "dimethyl phthalate", "expected": True, "category": "Phthalate"},
        {"ingredient": "diethyl phthalate", "expected": True, "category": "Phthalate"},
        
        # Other harmful ingredients
        {"ingredient": "triclosan", "expected": True, "category": "Antimicrobial"},
        {"ingredient": "benzophenone", "expected": True, "category": "UV Filter"},
        {"ingredient": "diethanolamine", "expected": True, "category": "Ethanolamine"},
        {"ingredient": "triethanolamine", "expected": True, "category": "Ethanolamine"},
        {"ingredient": "toluene", "expected": True, "category": "Solvent"},
        {"ingredient": "bha", "expected": True, "category": "Preservative"},
        {"ingredient": "bht", "expected": True, "category": "Preservative"},
        {"ingredient": "lead acetate", "expected": True, "category": "Heavy Metal"},
        {"ingredient": "mercury", "expected": True, "category": "Heavy Metal"},
        {"ingredient": "hydroquinone", "expected": True, "category": "Skin Lightener"},
        
        # Safe ingredients - Natural oils and butters
        {"ingredient": "jojoba oil", "expected": False, "category": "Natural Oil"},
        {"ingredient": "argan oil", "expected": False, "category": "Natural Oil"},
        {"ingredient": "coconut oil", "expected": False, "category": "Natural Oil"},
        {"ingredient": "shea butter", "expected": False, "category": "Natural Butter"},
        {"ingredient": "cocoa butter", "expected": False, "category": "Natural Butter"},
        
        # Safe ingredients - Vitamins and derivatives
        {"ingredient": "vitamin e", "expected": False, "category": "Vitamin"},
        {"ingredient": "vitamin c", "expected": False, "category": "Vitamin"},
        {"ingredient": "tocopherol", "expected": False, "category": "Vitamin"},
        {"ingredient": "niacinamide", "expected": False, "category": "Vitamin"},
        {"ingredient": "panthenol", "expected": False, "category": "Vitamin"},
        
        # Safe ingredients - Humectants and moisturizers
        {"ingredient": "glycerin", "expected": False, "category": "Humectant"},
        {"ingredient": "hyaluronic acid", "expected": False, "category": "Humectant"},
        {"ingredient": "aloe vera", "expected": False, "category": "Natural Extract"},
        {"ingredient": "allantoin", "expected": False, "category": "Skin Soother"},
        {"ingredient": "squalane", "expected": False, "category": "Moisturizer"},
        
        # Safe ingredients - Basic/Common
        {"ingredient": "water", "expected": False, "category": "Basic"},
        {"ingredient": "aqua", "expected": False, "category": "Basic"},
        {"ingredient": "glycine", "expected": False, "category": "Amino Acid"},
        {"ingredient": "arginine", "expected": False, "category": "Amino Acid"},
        {"ingredient": "xanthan gum", "expected": False, "category": "Thickener"}
    ]
    
    # Collect results
    results = []
    correct_predictions = 0
    category_stats = defaultdict(lambda: {"total": 0, "correct": 0})
    
    print("\nTesting predictions:")
    for test in test_cases:
        ingredient = test["ingredient"]
        expected = test["expected"]
        category = test["category"]
        result = classifier.predict(ingredient)
        
        if result:
            is_correct = result["is_harmful"] == expected
            if is_correct:
                correct_predictions += 1
                category_stats[category]["correct"] += 1
            
            category_stats[category]["total"] += 1
                
            results.append([
                ingredient,
                "Harmful" if expected else "Safe",
                "Harmful" if result["is_harmful"] else "Safe",
                f"{result['confidence']:.2f}",
                f"{result['max_confidence']:.2f}",
                "✓" if is_correct else "✗",
                category,
                "Yes" if result["is_chemical"] else "No"
            ])
    
    # Calculate accuracy
    accuracy = (correct_predictions / len(test_cases)) * 100
    
    # Print results in a table
    headers = ["Ingredient", "Expected", "Predicted", "Avg Conf", "Max Conf", "Correct", "Category", "Chemical"]
    print("\n" + tabulate(results, headers=headers, tablefmt="grid"))
    print(f"\nOverall Accuracy: {accuracy:.1f}%")
    
    # Print analysis
    print("\nAnalysis:")
    harmful_correct = sum(1 for r in results if r[1] == "Harmful" and r[2] == "Harmful")
    harmful_total = sum(1 for r in results if r[1] == "Harmful")
    safe_correct = sum(1 for r in results if r[1] == "Safe" and r[2] == "Safe")
    safe_total = sum(1 for r in results if r[1] == "Safe")
    
    print(f"Harmful Ingredients Detection Rate: {(harmful_correct/harmful_total)*100:.1f}%")
    print(f"Safe Ingredients Detection Rate: {(safe_correct/safe_total)*100:.1f}%")
    
    # Print category-wise analysis
    print("\nCategory-wise Analysis:")
    for category, stats in sorted(category_stats.items()):
        accuracy = (stats["correct"] / stats["total"]) * 100
        print(f"{category:20} Accuracy: {accuracy:5.1f}% ({stats['correct']}/{stats['total']})")

if __name__ == "__main__":
    test_model() 