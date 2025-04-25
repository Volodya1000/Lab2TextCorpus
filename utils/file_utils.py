import pdfplumber
from docx import Document as DocxDocument

def extract_text(file_path):
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_path.endswith('.pdf'):
            with pdfplumber.open(file_path) as pdf:
                return '\n'.join(
                    page.extract_text(layout=True) 
                    for page in pdf.pages 
                    if page.extract_text()
                )
        elif file_path.endswith('.docx'):
            return '\n'.join(par.text for par in DocxDocument(file_path).paragraphs)
        return None
    except Exception:
        return None