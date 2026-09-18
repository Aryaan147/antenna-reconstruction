"""Extract text AND structured parameter tables from the papers in data/raw/papers.

Writes:
  data/raw/extracted_text/<name>.txt        full text
  data/raw/extracted_tables/<name>.json     parsed symbol -> value tables
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from antenna_reconstruction.geometry_extraction.ingestion.pdf import extract_pdf

PDF_DIR = "data/raw/papers"
TEXT_DIR = "data/raw/extracted_text"
TABLE_DIR = "data/raw/extracted_tables"


def main() -> None:
    os.makedirs(TEXT_DIR, exist_ok=True)
    os.makedirs(TABLE_DIR, exist_ok=True)

    for filename in sorted(os.listdir(PDF_DIR)):
        if not filename.endswith(".pdf"):
            continue
        name = filename[: -len(".pdf")]
        doc = extract_pdf(os.path.join(PDF_DIR, filename), source_id=name)

        with open(os.path.join(TEXT_DIR, f"{name}.txt"), "w") as f:
            f.write(doc.text)

        payload = {
            "source_id": doc.source_id,
            "parameter_tables": [pt.model_dump() for pt in doc.parameter_tables],
        }
        with open(os.path.join(TABLE_DIR, f"{name}.json"), "w") as f:
            json.dump(payload, f, indent=2)

        n_params = len(doc.merged_parameters())
        print(
            f"{name:<32} tables={len(doc.tables):<3} "
            f"parameter_tables={len(doc.parameter_tables):<3} symbols={n_params}"
        )


if __name__ == "__main__":
    main()
