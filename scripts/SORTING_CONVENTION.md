# Image Sorting Convention

Raw photos from iPhone and Android go into:

- `public/images/primary/raw/iphone/`
- `public/images/primary/raw/android/`

## Folder separator system

Before photographing documents in an archival folder, a photo is taken of the folder itself (label/cover). This acts as a separator. The sorting script should:

1. Scan images in chronological order (by filename/EXIF timestamp)
2. Detect folder-cover photos (manually tagged, or by naming convention TBD)
3. Group subsequent document photos under that folder name
4. Output sorted subdirectories into `public/images/primary/sorted/<folder-name>/`

## Secondary sources

Non-archival reference images (books, articles, scans from other sources) go into:
`public/images/secondary-sources/`
