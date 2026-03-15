"""Build HCP-MMP (Glasser 2016) surface atlas BIDS outputs.

Extracts the cortical parcellation (HCP-MMP, 180 areas/hemisphere) from the
Q1-Q6 RelatedValidation210 CIFTI file distributed with the Tian 2020 MSA.
Produces per-hemisphere GIFTI label files in fsLR 32k space.
"""

from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

from scripts.utils import ensure_atlas_dir, write_tsv

SOURCEDATA = Path(__file__).parent.parent / "sourcedata" / "HCPex"
TIAN_SRC = Path("/media/storage/yalab-dev/Tian2020MSA_v1.4/Tian2020MSA/3T/Cortex-Subcortex")
CIFTI_FILE = (
    TIAN_SRC
    / "Q1-Q6_RelatedValidation210.CorticalAreas_dil_Final_Final_Areas_Group_Colors"
    ".32k_fs_LR_Tian_Subcortex_S1.dlabel.nii"
)

# fsLR 32k has 32492 vertices per hemisphere
N_VERTICES = 32492


def _cifti_label_to_mmp_name(cifti_name: str) -> str:
    """Convert 'L_V1_ROI' → 'V1_L'."""
    name = cifti_name.replace("_ROI", "")
    hemi, *parts = name.split("_")
    return "_".join(parts) + "_" + hemi


def _extract_gifti(
    cifti_data: np.ndarray,
    bm_ax: nib.cifti2.BrainModelAxis,
    label_ax: nib.cifti2.LabelAxis,
    mmp_df: pd.DataFrame,
    structure: str,
    hemi: str,
) -> nib.gifti.GiftiImage:
    """Build a GIFTI label image for one hemisphere."""
    # Find brain model for this structure
    for name, slc, bm in bm_ax.iter_structures():
        if name == structure:
            break

    # Dense vertex data for this hemisphere (medial wall = 0)
    vertex_data = np.zeros(N_VERTICES, dtype=np.int32)
    cifti_labels = label_ax.label[0]  # dict: key → (name, rgba)

    # Map CIFTI indices → mmp regionID via case-insensitive name matching
    mmp_lower = {row["regionName"].lower(): int(row["regionID"]) for _, row in mmp_df.iterrows()}
    cifti_key_to_region_id: dict[int, int] = {}
    for key, (cname, _) in cifti_labels.items():
        if key == 0 or not cname.startswith(hemi + "_"):
            continue
        mmp_name = _cifti_label_to_mmp_name(cname)
        region_id = mmp_lower.get(mmp_name.lower())
        if region_id is not None:
            cifti_key_to_region_id[int(key)] = region_id

    # Assign region IDs to cortical vertices
    region_ids = np.array(
        [cifti_key_to_region_id.get(int(v), 0) for v in cifti_data[slc]], dtype=np.int32
    )
    vertex_data[bm.vertex] = region_ids

    # Build GIFTI label table
    label_table = nib.gifti.GiftiLabelTable()
    label_table.labels.append(nib.gifti.GiftiLabel(key=0, red=1.0, green=1.0, blue=1.0, alpha=0.0))
    label_table.labels[0].label = "???"

    for _, row in mmp_df[mmp_df["LR"] == hemi].sort_values("regionID").iterrows():
        r, g, b = row["r"] / 255, row["g"] / 255, row["b"] / 255
        lbl = nib.gifti.GiftiLabel(key=int(row["regionID"]), red=r, green=g, blue=b, alpha=1.0)
        lbl.label = row["regionName"]
        label_table.labels.append(lbl)

    darray = nib.gifti.GiftiDataArray(
        data=vertex_data,
        intent=nib.nifti1.intent_codes["NIFTI_INTENT_LABEL"],
        datatype="NIFTI_TYPE_INT32",
        meta=nib.gifti.GiftiMetaData({"AnatomicalStructurePrimary": structure.replace("CIFTI_STRUCTURE_", "")}),
    )
    gii = nib.gifti.GiftiImage(darrays=[darray])
    gii.labeltable = label_table
    return gii


def _load_mmp_colors() -> pd.DataFrame:
    """Load mmp_labels.csv and add RGB colors from HCPex LUT where available."""
    mmp = pd.read_csv(SOURCEDATA / "mmp_labels.csv")
    lut = pd.read_csv(SOURCEDATA / "HCPex_LookUpTable.txt", sep="\t")
    lut = lut.rename(columns={"#No.": "index", "Label": "regionLongName", "R": "r", "G": "g", "B": "b"})
    merged = mmp.merge(lut[["regionLongName", "r", "g", "b"]], on="regionLongName", how="left")
    merged[["r", "g", "b"]] = merged[["r", "g", "b"]].fillna(128).astype(int)
    return merged


def _build_tsv(mmp_df: pd.DataFrame) -> pd.DataFrame:
    out = mmp_df[[
        "regionID", "regionName", "regionLongName",
        "LR", "region", "Lobe", "cortex",
        "x-cog", "y-cog", "z-cog", "volmm",
    ]].copy()
    return out.rename(columns={
        "regionID": "index",
        "regionName": "label",
        "regionLongName": "name",
        "LR": "hemisphere",
        "region": "region_abbrev",
        "Lobe": "lobe",
        "cortex": "cortex_type",
        "x-cog": "x_cog",
        "y-cog": "y_cog",
        "z-cog": "z_cog",
        "volmm": "volume_mm3",
    }).sort_values("index").reset_index(drop=True)


def build(base: Path) -> None:
    atlas_name = "HCPMMP"
    out_dir = ensure_atlas_dir(base, atlas_name)

    mmp_df = _load_mmp_colors()
    cifti = nib.load(CIFTI_FILE)
    cifti_data = cifti.get_fdata(dtype="float32")[0]
    bm_ax = cifti.header.get_axis(1)
    label_ax = cifti.header.get_axis(0)

    for hemi, structure in [
        ("L", "CIFTI_STRUCTURE_CORTEX_LEFT"),
        ("R", "CIFTI_STRUCTURE_CORTEX_RIGHT"),
    ]:
        gii = _extract_gifti(cifti_data, bm_ax, label_ax, mmp_df, structure, hemi)
        dst = out_dir / f"atlas-{atlas_name}_space-fsLR_hemi-{hemi}_dseg.label.gii"
        nib.save(gii, dst)

    df = _build_tsv(mmp_df)
    write_tsv(df, out_dir / f"atlas-{atlas_name}_dseg.tsv")
    print(f"  [HCPMMP] {len(df)} regions → {out_dir.name}/")
