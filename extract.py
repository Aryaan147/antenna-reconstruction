import os
from pypdf import PdfReader

pdf_dir = "data/raw/papers"
output_dir = "data/raw/extracted_text"
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(pdf_dir):
    if filename.endswith(".pdf"):
        filepath = os.path.join(pdf_dir, filename)
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        outpath = os.path.join(output_dir, filename.replace(".pdf", ".txt"))
        with open(outpath, "w") as f:
            f.write(text)
        print(f"Extracted {filename}")
