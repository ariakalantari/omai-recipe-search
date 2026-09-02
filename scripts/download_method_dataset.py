#!/usr/bin/env python3
"""Download the pinned instruction corpus used for deterministic enrichment."""

from __future__ import annotations

import argparse
import hashlib
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PINNED_COMMIT = "9db77df8c52c454f83dd2d6bdcde4580e3298498"
RAW_ROOT = f"https://raw.githubusercontent.com/kz882/recipe/{PINNED_COMMIT}"


@dataclass(frozen=True, slots=True)
class DownloadSpec:
    name: str
    size: int
    sha256: str


FILES = (
    DownloadSpec(
        "recipes_raw_nosource_ar.json",
        49_784_325,
        "93da2202eacb85ad81b50e49f9c1ceba33eb298f1c82a6d02eb59cab7d550cb5",
    ),
    DownloadSpec(
        "recipes_raw_nosource_epi.json",
        61_133_971,
        "08c7c8103a9c0dd114dc3fe01490fdf86ec9dee05d4db7d96504a61b5e8a886e",
    ),
    DownloadSpec(
        "LICENSE",
        20_437,
        "749689720d9b800da61e4a2936af9dd7df78ac6914181f04cab41b0ce5485eff",
    ),
)


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def valid_file(path: Path, spec: DownloadSpec) -> bool:
    return path.is_file() and path.stat().st_size == spec.size and file_digest(path) == spec.sha256


def download_file(output: Path, spec: DownloadSpec) -> None:
    target = output / spec.name
    if valid_file(target, spec):
        print(f"Pinned {spec.name} already present")
        return
    output.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        f"{RAW_ROOT}/{spec.name}",
        headers={"User-Agent": "omai-recipe-search/0.1"},
    )
    with tempfile.NamedTemporaryFile(dir=output, delete=False) as temporary:
        temporary_path = Path(temporary.name)
        digest = hashlib.sha256()
        downloaded = 0
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > spec.size:
                        raise RuntimeError(f"{spec.name} exceeded its pinned size")
                    digest.update(chunk)
                    temporary.write(chunk)
            if downloaded != spec.size or digest.hexdigest() != spec.sha256:
                raise RuntimeError(f"{spec.name} did not match its pinned checksum")
            temporary_path.replace(target)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
    print(f"Downloaded and verified {spec.name}")


def download(output: Path) -> None:
    for spec in FILES:
        download_file(output, spec)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/methods"))
    args = parser.parse_args()
    download(args.output)


if __name__ == "__main__":
    main()
