#!/usr/bin/env python3
"""Download the recipe archive supplied with the OMAI assignment."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

DATASET_URL = (
    "https://raw.githubusercontent.com/OMAI-dev/arbetsprov-recept/main/"
    "20170107-061401-recipeitems.json.zip"
)
ARCHIVE_MEMBER = "20170107-061401-recipeitems.json"
OUTPUT_FILE = "20170107-061401-recipeitems.jsonl"
EXPECTED_UNCOMPRESSED_BYTES = 141_698_284
MAX_UNCOMPRESSED_BYTES = 180 * 1024 * 1024
MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
DATASET_SHA256 = "4149d2d8677f26323b6da0300014c155abe1ba1f78af2c5c8e4f63f0b7df57f1"


def safe_extract(archive: zipfile.ZipFile, output: Path) -> None:
    members = [info for info in archive.infolist() if not info.is_dir()]
    matching = [info for info in members if Path(info.filename).name == ARCHIVE_MEMBER]
    if len(matching) != 1:
        raise RuntimeError(f"Dataset archive must contain exactly one {ARCHIVE_MEMBER!r} file")
    member = matching[0]
    if member.file_size != EXPECTED_UNCOMPRESSED_BYTES:
        raise RuntimeError("Dataset archive member size did not match the pinned source")
    if member.file_size > MAX_UNCOMPRESSED_BYTES:
        raise RuntimeError("Dataset archive is unexpectedly large")
    output.mkdir(parents=True, exist_ok=True)
    target = output / OUTPUT_FILE
    with archive.open(member) as source, target.open("wb") as destination:
        shutil.copyfileobj(source, destination)


def download(output: Path, url: str = DATASET_URL) -> None:
    target = output / OUTPUT_FILE
    if target.exists() and target.stat().st_size == EXPECTED_UNCOMPRESSED_BYTES:
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
    print(f"Downloaded OMAI assignment dataset to {output / OUTPUT_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/assignment"))
    parser.add_argument("--url", default=DATASET_URL)
    args = parser.parse_args()
    download(args.output, args.url)


if __name__ == "__main__":
    main()
