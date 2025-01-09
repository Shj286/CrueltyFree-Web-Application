import requests
from bs4 import BeautifulSoup
import json
import time
import re

class EWGScraper:
    def __init__(self):
        self.base_url = "https://www.ewg.org/skindeep/search/"
        self.ingredients_db = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_ingredient(self, name):
        """Scrape ingredient data from EWG's Skin Deep database"""
        try:
            # Search for the ingredient
            search_url = f"{self.base_url}?search={name}"
            response = self.session.get(search_url)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the ingredient link
            ingredient_link = soup.find('a', {'class': 'product-tile'}, href=re.compile(r'/skindeep/ingredients/'))
            if not ingredient_link:
                return None

            # Get ingredient details page
            detail_url = f"https://www.ewg.org{ingredient_link['href']}"
            detail_response = self.session.get(detail_url)
            if detail_response.status_code != 200:
                return None

            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            
            # Extract data
            hazard_score = self._extract_hazard_score(detail_soup)
            concerns = self._extract_concerns(detail_soup)
            categories = self._extract_categories(detail_soup)
            references = self._extract_references(detail_soup)

            data = {
                'name': name,
                'hazard_score': hazard_score,
                'concerns': concerns,
                'categories': categories,
                'references': references,
                'ewg_url': detail_url
            }

            # Cache the data
            self.ingredients_db[name.lower()] = data
            return data

        except Exception as e:
            print(f"Error scraping ingredient {name}: {str(e)}")
            return None

    def _extract_hazard_score(self, soup):
        """Extract hazard score from EWG page"""
        try:
            score_element = soup.find('div', {'class': 'hazard-score'})
            if score_element:
                score = score_element.text.strip()
                return int(re.search(r'\d+', score).group())
            return 0
        except:
            return 0

    def _extract_concerns(self, soup):
        """Extract health concerns from EWG page"""
        concerns = []
        try:
            concerns_section = soup.find('section', {'class': 'concerns'})
            if concerns_section:
                concern_items = concerns_section.find_all('div', {'class': 'concern-item'})
                for item in concern_items:
                    concern = item.find('h3').text.strip()
                    concerns.append(concern)
        except:
            pass
        return concerns

    def _extract_categories(self, soup):
        """Extract ingredient categories from EWG page"""
        categories = []
        try:
            categories_section = soup.find('section', {'class': 'categories'})
            if categories_section:
                category_items = categories_section.find_all('div', {'class': 'category-item'})
                for item in category_items:
                    category = item.text.strip()
                    categories.append(category)
        except:
            pass
        return categories

    def _extract_references(self, soup):
        """Extract scientific references from EWG page"""
        references = []
        try:
            references_section = soup.find('section', {'class': 'references'})
            if references_section:
                reference_items = references_section.find_all('div', {'class': 'reference-item'})
                for item in reference_items:
                    reference = item.text.strip()
                    references.append(reference)
        except:
            pass
        return references

    def get_all_ingredients(self):
        """Get all ingredients from the cached database"""
        return self.ingredients_db

    def get_harmful_ingredients(self):
        """Get all harmful ingredients (score >= 6) from the cached database"""
        return {
            name: info for name, info in self.ingredients_db.items()
            if int(info.get('hazard_score', 0)) >= 6
        } 