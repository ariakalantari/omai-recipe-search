# Data directory

`sample_recipes.json` is a tiny, synthetic development fixture committed to Git.

The full assignment dataset and all derived indexes are intentionally ignored. Put the provided
JSON file here and set `RECIPE_DATA_PATH`, or download the public Recipe Box development dataset:

```bash
uv run python scripts/download_dataset.py
```

Recipe Box is distributed under the ODC Attribution License. Its license is downloaded with the
data. The application does not require that particular dataset: the loader accepts JSON arrays,
JSON objects keyed by recipe ID, and JSON Lines.
