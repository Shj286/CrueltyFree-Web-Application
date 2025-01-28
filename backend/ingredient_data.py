import requests
from bs4 import BeautifulSoup
import json

class IngredientDataCollector:
    def __init__(self):
        self.sources = {
            'pubchem': 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/MolecularFormula,MolecularWeight,IUPACName/JSON',
            'cosing': 'https://ec.europa.eu/growth/tools-databases/cosing/index.cfm?fuseaction=search.details_v2&id={}',
            'openbeauty': 'https://openbeautyfacts.org/api/v0/product/{}',
            'chemidplus': 'https://chem.nlm.nih.gov/chemidplus/rn/{}'
        }
        
    def get_pubchem_data(self, ingredient):
        try:
            response = requests.get(self.sources['pubchem'].format(ingredient))
            if response.ok:
                data = response.json()
                return {
                    'formula': data['PropertyTable']['Properties'][0]['MolecularFormula'],
                    'weight': data['PropertyTable']['Properties'][0]['MolecularWeight'],
                    'iupac_name': data['PropertyTable']['Properties'][0]['IUPACName']
                }
        except:
            return None
            
    def get_cosing_data(self, ingredient):
        """European Commission cosmetic ingredient database"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(
                'https://ec.europa.eu/growth/tools-databases/cosing/index.cfm',
                params={'fuseaction': 'search.results', 'search': ingredient},
                headers=headers
            )
            soup = BeautifulSoup(response.text, 'html.parser')
            return {
                'eu_regulation': self._parse_cosing_regulation(soup),
                'restrictions': self._parse_cosing_restrictions(soup),
                'functions': self._parse_cosing_functions(soup)
            }
        except:
            return None
            
    def get_chemidplus_data(self, ingredient):
        """NIH Chemical database"""
        try:
            response = requests.get(
                f'https://chem.nlm.nih.gov/api/data/search',
                params={'q': ingredient}
            )
            if response.ok:
                data = response.json()
                return {
                    'toxicity': data.get('toxicity', []),
                    'health_effects': data.get('health_effects', []),
                    'safety_data': data.get('safety', {})
                }
        except:
            return None

    def get_comprehensive_data(self, ingredient):
        """Collect data from all sources"""
        data = {
            'pubchem': self.get_pubchem_data(ingredient),
            'cosing': self.get_cosing_data(ingredient),
            'chemidplus': self.get_chemidplus_data(ingredient)
        }
        return {k: v for k, v in data.items() if v is not None} 