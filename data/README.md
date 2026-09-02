# Data directory

`sample_recipes.json` is a tiny, synthetic development fixture committed to Git.

The full assignment dataset and all derived indexes are intentionally ignored. Download the exact
archive supplied in OMAI's public assignment repository:

```bash
uv run python scripts/download_dataset.py
```

The archive contains JSON Lines despite its `.json` filename. The download script verifies the
pinned SHA-256 digest and extracts it as `.jsonl` so the streaming format is explicit. The
application remains dataset-agnostic: the loader accepts JSON arrays, JSON objects keyed by recipe
ID, and JSON Lines.
