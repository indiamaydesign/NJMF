# Setup

## Requirements

- Python 3.10+
- pip

## Install dependencies

From the `scripts/` folder:

```bash
cd scripts
pip3 install -r requirements.txt
```

## Sort archival images

Drop your photos into:

- `public/images/primary/raw/iphone/`
- `public/images/primary/raw/android/`

Then run the sorting script from the `scripts/` folder:

```bash
# Preview first (no files are copied)
python3 sort_images.py --source ../public/images/primary/raw/iphone --dry-run

# Run for real
python3 sort_images.py --source ../public/images/primary/raw/iphone

# Same for Android photos
python3 sort_images.py --source ../public/images/primary/raw/android
```

The script walks through your photos in chronological order. When it hits a folder-cover photo (your separator), you type the folder name and all the following photos are copied into `public/images/primary/sorted/<folder-name>/` until the next separator.

## Secondary sources

Non-archival images (books, articles, other scans) go directly into:
`public/images/secondary-sources/`
