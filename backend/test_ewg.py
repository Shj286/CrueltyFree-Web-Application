from ingredient_api import scrape_ewg_data

def test_ewg_scraper():
    test_ingredients = [
        'methylparaben',
        'oxybenzone',
        'titanium dioxide'
    ]
    
    for ingredient in test_ingredients:
        print(f"\nTesting EWG scraper for: {ingredient}")
        data = scrape_ewg_data(ingredient)
        if data:
            print(f"Hazard Score: {data['hazard_score']}")
            print(f"Concerns: {data['concerns']}")
            print(f"Found in: {data['found_in']}")
        else:
            print("Failed to get data")

if __name__ == "__main__":
    test_ewg_scraper() 