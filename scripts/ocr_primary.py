#!/usr/bin/env python3
"""OCR all primary archive images referenced in timeline DATA using macOS Vision."""

import re, json, os
from pathlib import Path

import Vision
import Quartz

PREVIEWS_DIR = Path("/Users/India/NJMF/public/images/previews")
OUTPUT_DIR   = Path("/Users/India/NJMF/data/primary/ocr")
TIMELINE     = Path("/Users/India/NJMF/public/timeline.html")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def ocr_image(image_path: Path) -> str:
    url = Quartz.CFURLCreateFromFileSystemRepresentation(
        None, str(image_path).encode(), len(str(image_path).encode()), False
    )
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    cg  = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)

    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["nb-NO", "no-NO", "en-US"])
    req.setUsesLanguageCorrection_(True)

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, {})
    ok, err = handler.performRequests_error_([req], None)
    if not ok or err:
        return ""
    return "\n".join(o.topCandidates_(1)[0].string() for o in req.results())


def main():
    html = TIMELINE.read_text()
    match = re.search(r'const DATA\s*=\s*(\[.*?\]);', html, re.DOTALL)
    data  = json.loads(match.group(1))
    stems = [e["stem"] for e in data]

    print(f"OCR-ing {len(stems)} primary archive images…\n")

    results = {}
    missing = []

    for i, stem in enumerate(stems, 1):
        img = PREVIEWS_DIR / f"{stem}.jpg"
        if not img.exists():
            print(f"[{i:>3}/{len(stems)}] MISSING: {stem}.jpg")
            missing.append(stem)
            results[stem] = ""
            continue

        print(f"[{i:>3}/{len(stems)}] {stem}.jpg", end=" … ", flush=True)
        text = ocr_image(img)
        results[stem] = text

        out = OUTPUT_DIR / f"{stem}.txt"
        out.write_text(text, encoding="utf-8")
        words = len(text.split())
        print(f"{words} words")

    # Write index JSON
    index_path = OUTPUT_DIR / "index.json"
    index_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nDone. {len(stems) - len(missing)} OCR'd, {len(missing)} missing.")
    if missing:
        print("Missing:", missing)


if __name__ == "__main__":
    main()
