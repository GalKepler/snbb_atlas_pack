from pathlib import Path

import pandas as pd


def ensure_atlas_dir(base: Path, atlas_name: str) -> Path:
    d = base / "atlases" / f"atlas-{atlas_name}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_tsv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, sep="\t", index=False)
