#!/usr/bin/env python3
"""OCR all HEIC pages from Avtalt Spill 2010 using macOS Vision framework."""

import os
import json
import subprocess
import tempfile
from pathlib import Path

import Vision
import Quartz
import objc

SOURCE_DIR = Path("/Users/India/NJMF/public/images/secondary-sources/Avtalt Spill 2010")
OUTPUT_DIR = Path("/Users/India/NJMF/data/secondary-sources/avtalt-spill-2010")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def heic_to_png(heic_path: Path, tmp_dir: str) -> Path:
    """Convert HEIC to PNG using sips."""
    png_path = Path(tmp_dir) / (heic_path.stem + ".png")
    subprocess.run(
        ["sips", "-s", "format", "png", str(heic_path), "--out", str(png_path)],
        check=True,
        capture_output=True,
    )
    return png_path


def ocr_image(image_path: Path) -> str:
    """Run macOS Vision OCR on an image file, return recognised text."""
    url = Quartz.CFURLCreateFromFileSystemRepresentation(
        None, str(image_path).encode("utf-8"), len(str(image_path).encode("utf-8")), False
    )
    image_source = Quartz.CGImageSourceCreateWithURL(url, None)
    cg_image = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    # Norwegian + English
    request.setRecognitionLanguages_(["nb-NO", "no-NO", "en-US"])
    request.setUsesLanguageCorrection_(True)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
    success, error = handler.performRequests_error_([request], None)

    if not success or error:
        print(f"  Vision error: {error}")
        return ""

    lines = []
    for observation in request.results():
        candidate = observation.topCandidates_(1)[0]
        lines.append(candidate.string())

    return "\n".join(lines)


def extract_page_number(text: str) -> int | None:
    """Try to find a page number in the OCR'd text (usually at top or bottom)."""
    import re
    # Look for standalone numbers that are plausibly page numbers (1–400)
    candidates = re.findall(r"(?:^|\n)\s*(\d{1,3})\s*(?:\n|$)", text)
    for c in candidates:
        n = int(c)
        if 1 <= n <= 400:
            return n
    return None


def main():
    heic_files = sorted(SOURCE_DIR.glob("*.HEIC"))
    print(f"Found {len(heic_files)} HEIC files.")

    results = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, heic in enumerate(heic_files, 1):
            print(f"[{i}/{len(heic_files)}] OCR: {heic.name} ...", end=" ", flush=True)

            try:
                png = heic_to_png(heic, tmp_dir)
                text = ocr_image(png)
                page_num = extract_page_number(text)
                print(f"page ~{page_num}" if page_num else "page? (no number found)")
            except Exception as e:
                print(f"ERROR: {e}")
                text = ""
                page_num = None

            results.append({
                "filename": heic.name,
                "detected_page": page_num,
                "text": text,
            })

    # Sort by detected page number, unknowns at end
    results.sort(key=lambda r: (r["detected_page"] is None, r["detected_page"] or 9999))

    # Write individual text files
    for r in results:
        label = f"p{r['detected_page']:03d}" if r["detected_page"] else r["filename"].replace(".HEIC", "")
        txt_path = OUTPUT_DIR / f"{label}.txt"
        txt_path.write_text(r["text"], encoding="utf-8")

    # Write manifest JSON
    manifest = [
        {"filename": r["filename"], "detected_page": r["detected_page"], "text_file": f"p{r['detected_page']:03d}.txt" if r["detected_page"] else r["filename"].replace(".HEIC", ".txt")}
        for r in results
    ]
    manifest_path = OUTPUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write one combined text file (pages in order)
    combined_path = OUTPUT_DIR / "avtalt-spill-2010-full.txt"
    combined_parts = []
    for r in results:
        header = f"\n\n--- {r['filename']} | page {r['detected_page'] or '?'} ---\n\n"
        combined_parts.append(header + r["text"])
    combined_path.write_text("\n".join(combined_parts), encoding="utf-8")

    print(f"\nDone. Output in {OUTPUT_DIR}")
    print(f"  {len(results)} pages OCR'd")
    print(f"  Combined text: {combined_path}")
    print(f"  Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
