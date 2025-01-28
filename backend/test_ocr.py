import pytesseract
from PIL import Image

def test_ocr():
    try:
        # Test if tesseract is installed
        print("Tesseract version:", pytesseract.get_tesseract_version())
        
        # Test if pytesseract can find tesseract
        print("Tesseract command:", pytesseract.pytesseract.tesseract_cmd)
        
        return "OCR setup is working correctly"
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print(test_ocr()) 