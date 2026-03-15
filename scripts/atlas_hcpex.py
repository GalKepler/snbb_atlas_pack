"""Build HCPex atlas BIDS outputs.

Merges HCPex_LookUpTable.txt + mmp_labels.csv to produce a unified TSV,
following the merge logic demonstrated in notebooks/hcpex.ipynb.
"""

import shutil
from pathlib import Path

import pandas as pd

from scripts.utils import ensure_atlas_dir, write_tsv

SOURCEDATA = Path(__file__).parent.parent / "sourcedata" / "HCPex"


def _build_tsv() -> pd.DataFrame:
    lut = pd.read_csv(SOURCEDATA / "HCPex_LookUpTable.txt", sep="\t")
    lut = lut.rename(columns={"#No.": "index", "Label": "name", "Name:": "label_col", "R": "r", "G": "g", "B": "b"})

    mmp = pd.read_csv(SOURCEDATA / "mmp_labels.csv")

    merged = lut.merge(mmp, left_on="name", right_on="regionLongName", how="left")
    # Drop background row
    merged = merged[merged["index"] != 0].copy()

    # Derive hemisphere from name suffix
    merged["hemisphere"] = merged["name"].apply(
        lambda n: "R" if n.endswith("_R") else ("L" if n.endswith("_L") else None)
    )

    cols = [
        "index", "label", "name", "hemisphere",
        "lobe", "cortex", "regionID",
        "r", "g", "b",
        "x-cog", "y-cog", "z-cog", "volmm",
    ]
    # Use regionName as label where available, fall back to name
    merged["label"] = merged["regionName"].fillna(merged["name"])

    # Select and rename final columns
    out = merged[["index", "label", "name", "hemisphere", "Lobe", "cortex", "regionID",
                   "r", "g", "b", "x-cog", "y-cog", "z-cog", "volmm"]].copy()
    out = out.rename(columns={
        "Lobe": "lobe",
        "cortex": "cortex_type",
        "regionID": "region_id",
        "x-cog": "x_cog",
        "y-cog": "y_cog",
        "z-cog": "z_cog",
        "volmm": "volume_mm3",
    })
    return out.sort_values("index").reset_index(drop=True)


def build(base: Path) -> None:
    atlas_name = "HCPex"
    out_dir = ensure_atlas_dir(base, atlas_name)

    # Copy NIfTI
    src_nii = SOURCEDATA / "atlas-HCPex_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz"
    dst_nii = out_dir / f"atlas-{atlas_name}_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz"
    shutil.copy2(src_nii, dst_nii)

    # Write TSV
    df = _build_tsv()
    write_tsv(df, out_dir / f"atlas-{atlas_name}_dseg.tsv")
    print(f"  [HCPex] {len(df)} regions → {out_dir.name}/")
