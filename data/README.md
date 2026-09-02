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

The archive is extracted into the dedicated `data/assignment` directory. Keeping it separate from
other local recipe files prevents an old development corpus from being indexed accidentally.

The assignment archive contains methods for only a handful of records. Build the method-complete
review profile with:

```bash
uv run python scripts/download_method_dataset.py
uv run python scripts/enrich_dataset.py
```

The second downloader retrieves the Allrecipes and Epicurious Recipe Box exports from a full
commit SHA and verifies exact file sizes and SHA-256 digests. The enrichment requires an exact
normalized title, publisher-family compatibility, and at least 90 percent ingredient coverage in
both directions. Ambiguous methods are rejected. The resulting `data/enriched/recipes.jsonl` is a
deterministic 10,000-record subset of OMAI recipes with complete method coverage.

These generated files remain ignored by Git. See `THIRD_PARTY_NOTICES.md` for provenance and the
content-rights caveat.
