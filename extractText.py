import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pymongo import MongoClient
from PIL import Image

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['pdf_text_db']
collection = db['pdf_text']

# Function to extract text using pytesseract (for image-based PDFs)
def extract_text_from_image(pdf_path):
    text = ""
    images = convert_from_path(pdf_path)  # Convert PDF pages to images
    for image in images:
        text += pytesseract.image_to_string(image)  # Perform OCR on each image
    return text

# Extract text using pdfplumber (for PDFs with embedded text layers)
def extract_text_from_pdf_with_pdfplumber(pdf_path):
    extracted_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text  # Extract text from each page
            else:
                print(f"Warning: No text extracted from page {page.page_number}")
    
    if not extracted_text:
        print("No text extracted with pdfplumber. Switching to OCR.")
        extracted_text = extract_text_from_image(pdf_path)  # Fallback to OCR using pytesseract

    return extracted_text

# Save text to MongoDB (handling 16MB limit)
def save_text_to_mongodb(text):
    if len(text.encode('utf-8')) > 16 * 1024 * 1024:
        chunks = [text[i:i + 16 * 1024 * 1024 // 2] for i in range(0, len(text), 16 * 1024 * 1024 // 2)]
        for i, chunk in enumerate(chunks):
            collection.insert_one({"chunk_id": i, "text": chunk})
        print(f"Text saved in {len(chunks)} chunks due to size limit.")
    else:
        if text:
            collection.insert_one({"text": text})
            print("Text saved in MongoDB.")
        else:
            print("No text to save to MongoDB.")

# Example usage
pdf_path = './pdf.pdf'
text = extract_text_from_pdf_with_pdfplumber(pdf_path)

# Print extracted text for debugging purposes
print(f"Extracted text (first 1000 characters): {text[:1000]}...")

# Save extracted text to MongoDB
save_text_to_mongodb(text)

# Function to verify and print text saved in MongoDB
def verify_text_in_mongodb():
    docs = collection.find()
    for doc in docs:
        chunk_id = doc.get('chunk_id', 'N/A')  # Retrieve chunk ID if present
        text_data = doc.get('text', '[No Text Found]')  # Retrieve text data
        if text_data != '[No Text Found]':
            print(f"Chunk ID: {chunk_id}")
            print(f"Text: {text_data[:1000]}...")  # Print only the first 1000 characters for brevity
        else:
            print("No text was found in the document.")

verify_text_in_mongodb()
