#!/usr/bin/env python3
import os
import subprocess
import glob

def main():
    # The directory where this script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # The target directory for extracted images
    images_dir = os.path.join(base_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Find all PDFs in the base directory
    pdfs = glob.glob(os.path.join(base_dir, "*.pdf"))
    
    if not pdfs:
        print(f"No PDFs found in {base_dir}")
        return

    for pdf in pdfs:
        pdf_name = os.path.splitext(os.path.basename(pdf))[0]
        print(f"Extracting images from {pdf_name}.pdf...")
        
        # We use 'pdfimages' to extract embedded images losslessly.
        # -png: Convert extracted images to PNG format
        prefix = os.path.join(images_dir, f"{pdf_name}_")
        
        try:
            subprocess.run(["pdfimages", "-png", pdf, prefix], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error extracting images from {pdf_name}.pdf: {e}")
            
    print("\nExtraction complete!")
    print(f"You can find the extracted images in: {images_dir}")
    print("Select the correct figure for each paper, move it to data/raw/papers/, and rename it to match the PDF name (e.g., paper_name.png).")

if __name__ == "__main__":
    main()
