import unittest
import mongomock
from unittest.mock import patch
from pymongo import MongoClient
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

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
def save_text_to_mongodb(collection, text):
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

# Function to verify and print text saved in MongoDB
def verify_text_in_mongodb(collection):
    docs = collection.find()
    for doc in docs:
        chunk_id = doc.get('chunk_id', 'N/A')  # Retrieve chunk ID if present
        text_data = doc.get('text', '[No Text Found]')  # Retrieve text data
        if text_data != '[No Text Found]':
            print(f"Text: {text_data}")
        else:
            print("No text was found in the document.")

# Unit tests
class TestPDFTextExtraction(unittest.TestCase):

    @patch('pymongo.MongoClient', new=mongomock.MongoClient)  # Mock MongoDB connection
    def setUp(self):
        self.client = mongomock.MongoClient()
        self.db = self.client['pdf_text_db']
        self.collection = self.db['pdf_text']
        self.pdf_path = './pdf.pdf'  # Use mock PDF

    def tearDown(self):
        self.client.close()  # Ensure the client is closed

    @patch('pdfplumber.open')
    def test_pdfplumber_text_extraction(self, mock_pdfplumber_open):
        # Mock PDF setup
        mock_pdf = mock_pdfplumber_open.return_value
        mock_pdf.pages = [unittest.mock.Mock() for _ in range(3)]
        for page in mock_pdf.pages:
            page.extract_text.return_value = "Some extracted text."

        # Run your text extraction function
        extracted_text = extract_text_from_pdf_with_pdfplumber(self.pdf_path)

        # Assert that the text is not empty (or contains some expected substring)
        self.assertTrue(len(extracted_text) > 0, "No text was extracted.")

    @patch('pytesseract.image_to_string')
    @patch('pdf2image.convert_from_path')
    def test_pytesseract_image_extraction(self, mock_convert_from_path, mock_image_to_string):
        # Set the mock return value for OCR text
        mock_image_to_string.return_value = "Some OCR text."

        # Mock the image conversion from the PDF
        mock_image = Image.new('RGB', (100, 100))
        mock_convert_from_path.return_value = [mock_image]

        # Call the function under test
        extracted_text = extract_text_from_image(self.pdf_path)

        # Assert that something was extracted
        self.assertTrue(len(extracted_text) > 0, "No OCR text was extracted.")

    def test_text_saving_to_mongodb(self):
        # Call the function to save text
        text = "Some test text for MongoDB."
        save_text_to_mongodb(self.collection, text)  # Pass the mocked collection

        # Check that at least one document was saved
        docs = list(self.collection.find())
        print(f"Documents found: {len(docs)}")  # Debugging line
        self.assertTrue(len(docs) > 0, "No documents found in MongoDB.")

        # Optionally, you can check the specific content saved if needed
        saved_text = docs[0].get('text', '')
        self.assertTrue(saved_text, "The saved document has no text content.")

    def test_verify_text_in_mongodb(self):
        # Add mock data to the collection
        self.collection.insert_one({"text": "This is a test for verification."})

        # Run verification function and check output
        verify_text_in_mongodb(self.collection)

if __name__ == '__main__':
    unittest.main()
