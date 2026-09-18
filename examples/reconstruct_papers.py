"""Run the template-driven pipeline over every paper in data/raw/papers."""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from antenna_reconstruction.template_pipeline import TemplatePipeline

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    pipeline = TemplatePipeline()

    papers = sorted(glob.glob("data/raw/papers/*.pdf"))
    if not papers:
        print("No PDFs found under data/raw/papers.")
        return

    succeeded = verified = 0
    for path in papers:
        name = os.path.basename(path)[: -len(".pdf")]
        result = pipeline.run_from_pdf(path, os.path.join(OUT_DIR, f"{name}.dxf"))
        print(result.render())
        print()
        succeeded += result.success
        verified += result.verified

    print(f"{succeeded}/{len(papers)} reconstructed, {verified} of those verified.")


if __name__ == "__main__":
    main()
