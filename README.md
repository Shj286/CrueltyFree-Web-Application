# CrueltyFree Product Analyzer

A web application that analyzes cosmetic and personal care product ingredients for harmful substances and provides safety information.

## Features

- OCR-based ingredient extraction from product images
- Analysis of ingredients against a comprehensive toxic chemicals database
- Integration with EWG's Skin Deep database
- Safety scoring and categorization of harmful ingredients
- Detailed information about ingredient concerns and safer alternatives
- Used Machine Learning techniques to improve the classification accuracy


## Tech Stack

- Backend: Python/Flask
- Frontend: HTML/CSS/JavaScript
- OCR: Tesseract
- Database: JSON-based ingredient database
- Machine Learning: Scikit-learn

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CrueltyFree.git
cd CrueltyFree
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the backend server:
```bash
cd backend
python app.py
```

5. Start the frontend server:
```bash
cd frontend
python -m http.server 8000
```

6. Open your browser and navigate to `http://localhost:8000`

## Project Structure

```
CrueltyFree/
├── backend/
│   ├── app.py                         # Main Flask application
│   ├── ingredient_scraper.py          # Ingredient analysis logic
│   ├── ewg_scraper.py                # EWG data integration
│   └── toxic_chemicals_database.json  # Ingredient database
├── frontend/
│   ├── index.html                    # Main HTML file
│   └── app.css                       # Styles
└── requirements.txt                   # Python dependencies
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
