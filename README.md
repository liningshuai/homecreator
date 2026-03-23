# Home Creator

Static mirror and scraping toolkit for the Home Creator storefront.

This repository contains:

- a local static export of `https://www.homecreator.com.au`
- a Python scraper used to download Shopify pages and assets
- small post-processing scripts for navigation and gallery fixes

It is best understood as a deployment/export repository, not a typical application source repo.

## What is in this repo

The generated site lives in [`dump/`](./dump) and can be served locally as a static website.

Snapshot metadata in [`dump/scrape_stats.json`](./dump/scrape_stats.json) currently shows:

- source site: `https://www.homecreator.com.au`
- crawl depth: `3`
- pages scraped: `37`
- resources downloaded: `823`

Main exported sections include:

- home page
- collection pages
- product pages
- gallery pages
- policy pages
- contact / quote / guides / warranty / trade program pages

## Quick start

To preview the exported site locally:

```bash
cd dump
python -m http.server 8000
```

Then open `http://localhost:8000`.

Serving from the `dump/` directory is important because the exported HTML uses root-relative paths such as `/assets/...` and `/fonts/...`.

## Repository structure

```text
homecreator/
|-- dump/                  Static site export and downloaded assets
|-- shopify_scraper.py     Shopify site scraper
|-- fix.py                 Navigation/dropdown link fixer
|-- fix_gallery.py         Gallery image replacement helper
`-- README.md
```

## Scripts

### `shopify_scraper.py`

Downloads pages and assets from the live Shopify storefront and writes the result into `dump/`.

Key characteristics:

- targets `https://www.homecreator.com.au`
- follows internal Shopify pages up to depth `3`
- downloads HTML, CSS, fonts, images, and related assets
- saves crawl metadata to `dump/scrape_stats.json`

Install the Python dependencies before running it:

```bash
pip install requests beautifulsoup4 cssutils urllib3
python shopify_scraper.py
```

## `fix.py`

Applies dropdown/navigation fixes across exported HTML files.

Note: the current script contains hardcoded absolute paths in its default entry point. If you want to rerun it on another machine, update the paths in the script first.

## `fix_gallery.py`

Repairs gallery pages by extracting the correct image list from `window.__remixContext` and replacing the hardcoded gallery array.

The script also contains environment-specific default paths. For portable use, pass explicit file paths on the command line or update the defaults in `main()`.

Example:

```bash
python fix_gallery.py dump/pages/roller-blinds-gallery/index.html
python fix_gallery.py dump/pages/curtains-gallery/index.html
```

## Maintenance notes

- `dump/` is generated content, so large file diffs are expected.
- If the live Shopify site changes structure, the scraper or fix scripts may need updates.
- Some helper scripts were originally written in a machine-specific environment and are not fully parameterized yet.

## Use case

This repo is useful when you need to:

- host or inspect an offline/static copy of the storefront
- preserve a point-in-time snapshot of site content
- tweak exported HTML/CSS/JS after scraping
- rerun a Shopify scrape and compare the output
