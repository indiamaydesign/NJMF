#!/usr/bin/env python3
"""
Convert all raw HEIC/image files to JPEG previews for the web viewer.
Output: public/images/previews/<filename_stem>.jpg

Only regenerates files that are missing (safe to re-run).
"""

import sys
from pathlib import Path
from PIL import Image
import pillow_heif

pillow_heif.register_heif_opener()

ROOT     = Path(__file__).parent.parent
RAW_DIR  = ROOT / "public" / "images" / "primary" / "raw"
OUT_DIR  = ROOT / "public" / "images" / "previews"
MAX_SIDE = 2000
EXTS     = {".heic", ".jpg", ".jpeg", ".png", ".webp"}


def convert(src: Path, dst: Path) -> None:
    img = Image.open(src).convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        r = MAX_SIDE / max(w, h)
        img = img.resize((int(w * r), int(h * r)), Image.LANCZOS)
    img.save(dst, "JPEG", quality=88, optimize=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = sorted(p for p in RAW_DIR.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)
    print(f"Found {len(paths)} images. Converting to {OUT_DIR} …")

    done = skipped = errors = 0
    for i, src in enumerate(paths, 1):
        dst = OUT_DIR / (src.stem + ".jpg")
        if dst.exists():
            skipped += 1
            continue
        try:
            convert(src, dst)
            done += 1
        except Exception as e:
            print(f"  ERROR {src.name}: {e}", file=sys.stderr)
            errors += 1
        if i % 50 == 0:
            print(f"  {i}/{len(paths)}  (done={done} skipped={skipped} errors={errors})")

    print(f"Finished: {done} converted, {skipped} already existed, {errors} errors")


if __name__ == "__main__":
    main()
