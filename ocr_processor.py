import os
import re
import logging
import cv2
import numpy as np
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
from PIL import Image
from pdf2image import convert_from_path
from datetime import datetime



# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check if Tesseract is installed and available
def check_tesseract():
    """Check if Tesseract OCR is properly installed."""
    try:
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract version: {version}")
        return True
    except Exception as e:
        logger.error(f"Tesseract OCR not found: {e}")
        logger.error("Please ensure Tesseract OCR is installed on your system.")
        return False

# Image preprocessing to improve OCR results
def preprocess_image(image_path):
    """Preprocess image to improve OCR quality."""
    try:
        # Read image using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Failed to load image: {image_path}")
            return None
            
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding to get black and white image
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Save preprocessed image
        preprocessed_path = f"{image_path}_preprocessed.jpg"
        cv2.imwrite(preprocessed_path, opening)
        
        logger.debug(f"Image preprocessed: {preprocessed_path}")
        return preprocessed_path
    except Exception as e:
        logger.error(f"Error preprocessing image: {e}")
        # Fall back to original image
        return image_path

def extract_text_from_image(image_path, lang='eng'):
    """Extract text from an image using pytesseract OCR with improved settings."""
    if not check_tesseract():
        return "ERROR: Tesseract OCR not installed or configured properly."
    
    try:
        logger.debug(f"Processing image: {image_path}")
        
        # Preprocess image for better OCR results
        preprocessed_image = preprocess_image(image_path)
        if preprocessed_image is None:
            return ""
            
        # Use PIL to open the preprocessed image
        image = Image.open(preprocessed_image if preprocessed_image else image_path)
        
        # Apply OCR with advanced configurations
        text = pytesseract.image_to_string(
            image,
            lang=lang,
            config='--psm 6 --oem 3'  # Page segmentation mode: assume a single uniform block of text
        )
        
        # Clean up any temporary files
        if preprocessed_image and preprocessed_image != image_path and os.path.exists(preprocessed_image):
            os.remove(preprocessed_image)
        
        logger.debug(f"Extracted text length: {len(text)}")
        if not text.strip():
            logger.warning(f"No text extracted from image: {image_path}")
            
        return text
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}", exc_info=True)
        return f"ERROR: {str(e)}"

def extract_text_from_pdf(pdf_path, lang='eng'):
    """Extract text from a PDF by converting to images and using OCR."""
    if not check_tesseract():
        return "ERROR: Tesseract OCR not installed or configured properly."
    
    try:
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Convert PDF to images
        try:
            images = convert_from_path(pdf_path)
            logger.info(f"Converted PDF to {len(images)} images")
        except Exception as pdf_err:
            logger.error(f"Error converting PDF to images: {pdf_err}", exc_info=True)
            return f"ERROR: Failed to convert PDF to images: {str(pdf_err)}"
        
        if not images:
            return "ERROR: No images extracted from PDF"
        
        extracted_text = ""
        
        # Process each page
        for i, image in enumerate(images):
            # Save as temporary image
            temp_image_path = f"temp_page_{i}.jpg"
            image.save(temp_image_path, 'JPEG')
            logger.debug(f"Saved temporary image: {temp_image_path}")
            
            # Extract text from the image
            page_text = extract_text_from_image(temp_image_path, lang=lang)
            extracted_text += f"\n\n--- PAGE {i+1} ---\n\n{page_text}"
            
            # Clean up temp file
            try:
                os.remove(temp_image_path)
            except Exception as rm_err:
                logger.warning(f"Could not remove temp file: {rm_err}")
        
        if not extracted_text.strip():
            logger.warning(f"No text extracted from PDF: {pdf_path}")
            
        return extracted_text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}", exc_info=True)
        return f"ERROR: {str(e)}"

def extract_date(text):
    """Extract a date from the text of a receipt or statement."""
    # Try different date formats
    date_patterns = [
        r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{1,2}-\d{1,2}-\d{2,4})',  # MM-DD-YYYY or DD-MM-YYYY
        r'(\d{2,4}\.\d{1,2}\.\d{1,2})',  # YYYY.MM.DD
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2}),? \d{2,4}',  # Month DD, YYYY
        r'\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{2,4}'  # DD Month YYYY
    ]
    
    logger.debug("Searching for date in extracted text")
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Try to parse the date
            try:
                for match in matches:
                    # Try different date formats
                    for fmt in ['%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y', 
                               '%m-%d-%Y', '%m-%d-%y', '%d-%m-%Y', '%d-%m-%y',
                               '%Y.%m.%d', '%d.%m.%Y', '%B %d, %Y', '%b %d, %Y',
                               '%d %B %Y', '%d %b %Y']:
                        try:
                            date = datetime.strptime(match, fmt)
                            logger.info(f"Found date: {date.strftime('%Y-%m-%d')}")
                            return date.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
            except Exception as e:
                logger.debug(f"Error parsing date: {e}")
                continue
    
    # If no date found, return today's date
    today = datetime.now().strftime('%Y-%m-%d')
    logger.info(f"No date found, using today's date: {today}")
    return today

def extract_amounts(text):
    """Extract monetary amounts from text."""
    # Look for patterns like $XX.XX or XX.XX
    amount_patterns = [
        r'\$\s*(\d+(?:,\d{3})*\.\d{2})',  # $XX.XX with possible commas
        r'(\d+(?:,\d{3})*\.\d{2})',  # XX.XX with possible commas
        r'(\d+)\s*\.\s*(\d{2})'  # XX . XX (with possible spaces)
    ]
    
    logger.debug("Searching for amounts in extracted text")
    
    amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if isinstance(match, tuple):
                    # Handle the case where regex captures groups
                    amount = float(f"{match[0]}.{match[1]}")
                else:
                    # Clean up any commas
                    amount_str = match.replace(',', '')
                    amount = float(amount_str)
                amounts.append(amount)
                logger.debug(f"Found amount: {amount}")
            except ValueError:
                continue
    
    if not amounts:
        logger.warning("No amounts found in text")
    else:
        logger.info(f"Found {len(amounts)} amounts")
        
    return amounts

def extract_items(text):
    """Extract item descriptions and prices from receipt text."""
    items = []
    
    # Split text into lines
    lines = text.split('\n')
    
    logger.debug(f"Extracting items from {len(lines)} lines of text")
    
    # Process each line
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Look for price patterns
        amount_match = re.search(r'(\d+\.\d{2})', line)
        if amount_match:
            try:
                amount = float(amount_match.group(1))
                # Extract the description (everything before the price)
                description = line[:amount_match.start()].strip()
                
                # Clean up the description
                description = re.sub(r'\s+', ' ', description)
                
                # Only add if we have both description and amount
                if description and amount > 0:
                    items.append({
                        'description': description,
                        'amount': amount
                    })
                    logger.debug(f"Found item: {description} - ${amount}")
            except ValueError:
                continue
    
    if not items:
        logger.warning("No items extracted from text")
    else:
        logger.info(f"Found {len(items)} items")
        
    return items

def process_uploaded_file(file_path):
    """Process an uploaded file (PDF or image) and extract text."""
    file_extension = file_path.split('.')[-1].lower()
    
    logger.info(f"Processing uploaded file: {file_path} with extension {file_extension}")
    
    # First check if Tesseract is installed
    if not check_tesseract():
        error_message = "Tesseract OCR is not installed or configured properly. Please install Tesseract OCR on your system."
        logger.error(error_message)
        return error_message
    
    if file_extension == 'pdf':
        text = extract_text_from_pdf(file_path)
    elif file_extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'gif']:
        text = extract_text_from_image(file_path)
    else:
        error_message = f"Unsupported file format: {file_extension}"
        logger.error(error_message)
        raise ValueError(error_message)
    
    # If the text contains an error message, raise an exception
    if text.startswith("ERROR:"):
        logger.error(text)
        raise Exception(text[7:])  # Remove the "ERROR: " prefix
        
    if not text.strip():
        logger.warning(f"No text extracted from {file_path}")
    else:
        logger.info(f"Successfully extracted {len(text)} characters from {file_path}")
        
    return text
