#!/usr/bin/env python3
"""Download the public Recipe Box dataset used for development and evaluation."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DATASET_URL = "https://eightportions.com/recipes_raw.zip"
EXPECTED_FILES = {
    "recipes_raw_nosource_ar.json",
    "recipes_raw_nosource_epi.json",
    "recipes_raw_nosource_fn.json",
    "LICENSE",
}
MAX_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
DATASET_SHA256 = "1ae20f3260313d501edf23c22c6f1875e87917f5a8e2ff13b40450719322c81b"


def safe_extract(archive: zipfile.ZipFile, output: Path) -> None:
    names = {Path(info.filename).name for info in archive.infolist() if not info.is_dir()}
    missing = EXPECTED_FILES - names
    if missing:
        raise RuntimeError(f"Dataset archive is missing expected files: {sorted(missing)}")
    if sum(info.file_size for info in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
        raise RuntimeError("Dataset archive is unexpectedly large")
    output.mkdir(parents=True, exist_ok=True)
    for info in archive.infolist():
        filename = Path(info.filename).name
        if filename not in EXPECTED_FILES:
            continue
        target = output / filename
        with archive.open(info) as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)


def download(output: Path, url: str = DATASET_URL) -> None:
    if all((output / filename).exists() for filename in EXPECTED_FILES):
        print(f"Dataset already present in {output}")
        return
    with tempfile.NamedTemporaryFile(suffix=".zip") as temporary:
        request = urllib.request.Request(url, headers={"User-Agent": "omai-recipe-search/0.1"})
        with urllib.request.urlopen(request, timeout=60) as response:
            digest = hashlib.sha256()
            downloaded = 0
            while chunk := response.read(1024 * 1024):
                downloaded += len(chunk)
                if downloaded > MAX_COMPRESSED_BYTES:
                    raise RuntimeError("Dataset download is unexpectedly large")
                digest.update(chunk)
                temporary.write(chunk)
        if url == DATASET_URL and digest.hexdigest() != DATASET_SHA256:
            raise RuntimeError("Dataset archive checksum did not match the pinned source")
        temporary.flush()
        with zipfile.ZipFile(temporary.name) as archive:
            safe_extract(archive, output)
    print(f"Downloaded Recipe Box dataset to {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/recipes"))
    parser.add_argument("--url", default=DATASET_URL)
    args = parser.parse_args()
    download(args.output, args.url)


if __name__ == "__main__":
    main()
