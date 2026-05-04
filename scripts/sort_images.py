#!/usr/bin/env python3
"""
Sort archival photos into named folders based on folder-cover separators.

Convention: before photographing documents in an archival folder, take a photo
of the folder itself. This script detects those separator photos and groups the
subsequent document photos under that folder's name.

Usage:
    python3 sort_images.py --source ../public/images/primary/raw/iphone
    python3 sort_images.py --source ../public/images/primary/raw/android
    python3 sort_images.py --source ../public/images/primary/raw/iphone --dry-run
"""

import argparse
import shutil
import sys
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS

OUTPUT_DIR = Path(__file__).parent.parent / "public" / "images" / "primary" / "sorted"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}


def get_exif_datetime(path: Path) -> str | None:
    try:
        img = Image.open(path)
        exif_data = img._getexif()
        if not exif_data:
            return None
        for tag_id, value in exif_data.items():
            if TAGS.get(tag_id) == "DateTimeOriginal":
                return value
    except Exception:
        pass
    return None


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTENSIONS


def load_images_sorted(source: Path) -> list[Path]:
    images = [p for p in source.iterdir() if p.is_file() and is_image(p)]
    # Sort by EXIF datetime, falling back to filename
    def sort_key(p: Path) -> str:
        return get_exif_datetime(p) or p.name
    return sorted(images, key=sort_key)


def prompt_folder_name(image: Path, index: int) -> str:
    print(f"\n[{index}] Separator photo detected: {image.name}")
    print("      Enter the archival folder name (or press Enter to skip): ", end="")
    name = input().strip()
    return name


def sort_images(source: Path, dry_run: bool = False) -> None:
    images = load_images_sorted(source)
    if not images:
        print(f"No images found in {source}")
        return

    print(f"Found {len(images)} images in {source}")
    print("Images marked as separators will prompt you for a folder name.")
    print("All others are assigned to the most recent folder.\n")

    current_folder: str | None = None
    unassigned: list[Path] = []

    for i, image in enumerate(images):
        # Every image — ask if it's a separator
        # In practice you'd want a smarter heuristic; for now we ask interactively
        print(f"  [{i+1}/{len(images)}] {image.name}")
        print("      Is this a folder-cover separator? [y/N] ", end="")
        answer = input().strip().lower()

        if answer == "y":
            current_folder = prompt_folder_name(image, i + 1)
            if not current_folder:
                print("      Skipping separator (no name given).")
                continue
            dest_dir = OUTPUT_DIR / current_folder
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
            print(f"      -> New folder: {dest_dir}")
        else:
            if current_folder is None:
                unassigned.append(image)
                print("      -> No folder assigned yet, queued for later.")
                continue
            dest = OUTPUT_DIR / current_folder / image.name
            print(f"      -> {dest}")
            if not dry_run:
                (OUTPUT_DIR / current_folder).mkdir(parents=True, exist_ok=True)
                shutil.copy2(image, dest)

    if unassigned:
        print(f"\n{len(unassigned)} images had no folder assigned:")
        for p in unassigned:
            print(f"  {p.name}")
        print("Re-run after adding separators, or move them manually.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sort archival photos by folder-cover separators.")
    parser.add_argument("--source", required=True, help="Path to raw image folder (iphone or android)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without copying files")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    if not source.exists():
        print(f"Source folder not found: {source}", file=sys.stderr)
        sys.exit(1)

    sort_images(source, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
