#!/usr/bin/env python3
"""
Test script for OCR functionality.
Run this script to test if OCR is working correctly before using the full app.
"""

import os
import sys
import logging
from ocr_processor import process_uploaded_file, check_tesseract

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ocr(file_path):
    """Test OCR functionality on a specific file."""
    # Normalize the file path to handle any path issues
    file_path = os.path.normpath(file_path)
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} does not exist.")
        return False
    
    print(f"Testing OCR on file: {file_path}")
    print("=" * 50)
    
    # First check if Tesseract is installed
    if not check_tesseract():
        print("ERROR: Tesseract OCR is not installed or configured properly.")
        print("Please install Tesseract OCR and make sure it's in your PATH.")
        return False
    
    try:
        extracted_text = process_uploaded_file(file_path)
        
        if not extracted_text or not extracted_text.strip():
            print("WARNING: No text was extracted from the file.")
            return False
        
        # Print a sample of the extracted text
        print("\nExtracted Text Sample:")
        print("-" * 50)
        print(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
        print("-" * 50)
        print(f"\nTotal characters extracted: {len(extracted_text)}")
        print("\nOCR TEST SUCCESSFUL!")
        return True
    
    except Exception as e:
        print(f"ERROR during OCR processing: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_ocr.py <path_to_image_or_pdf>")
        sys.exit(1)
    
    # Get the file path from command line arguments
    file_path = sys.argv[1]
    
    # Remove any invisible characters that might have been copied
    file_path = file_path.strip()
    
    success = test_ocr(file_path)
    
    if not success:
        print("\nOCR TEST FAILED!")
        print("Please check the error messages above and fix any issues before using the main app.")
        sys.exit(1)
    
    sys.exit(0)