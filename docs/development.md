# Development

## Build Pipeline Architecture

```
main.py
  └── scripts/build_atlas_pack.py  (orchestrator)
        ├── atlas_tian.py          → atlases/atlas-TianS{1-4}/
        ├── atlas_hcpex.py         → atlases/atlas-HCPex/
        ├── atlas_hcpmmp.py        → atlases/atlas-HCPMMP/
        └── atlas_schaefer_tian.py → atlases/atlas-Schaefer2018N{N}n7Tian2020S{S}/ (×40)
```

Each module exposes a single `build(base: Path) -> None` function. The orchestrator calls them in sequence after writing `dataset_description.json`.

### Shared Utilities (`scripts/utils.py`)

```python
def ensure_atlas_dir(base: Path, atlas_name: str) -> Path:
    """Create atlases/atlas-<Name>/ and return its path."""

def write_tsv(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame as tab-separated values."""
```

## Adding a New Atlas

### 1. Add source data

Place raw files in `sourcedata/<AtlasName>/`, or document the external path in the module if the data is too large to version-control.

### 2. Create a build module

Add `scripts/atlas_<name>.py` following this pattern:

```python
from pathlib import Path
import shutil
import pandas as pd
from scripts.utils import ensure_atlas_dir, write_tsv

ATLAS_NAME = "MyAtlas"  # BIDS atlas entity value (CamelCase)


def _parse_labels() -> pd.DataFrame:
    """Read source files and return a DataFrame with at minimum:
    index (int), label (str), name (str), hemisphere (str)
    """
    ...


def build(base: Path) -> None:
    out_dir = ensure_atlas_dir(base, ATLAS_NAME)

    # Copy or generate the NIfTI/GIFTI
    src_nii = ...
    dst_nii = out_dir / f"atlas-{ATLAS_NAME}_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz"
    shutil.copy(src_nii, dst_nii)

    # Write the lookup table
    df = _parse_labels()
    write_tsv(df, out_dir / f"atlas-{ATLAS_NAME}_dseg.tsv")
```

**Minimum TSV columns:** `index`, `label`, `name`, `hemisphere`

### 3. Register in the orchestrator

Edit `scripts/build_atlas_pack.py`:

```python
def build() -> None:
    from scripts import atlas_hcpex, atlas_hcpmmp, atlas_schaefer_tian, atlas_tian
    from scripts import atlas_<name>   # add this

    # ... existing build calls ...
    atlas_<name>.build(BASE)           # add this
```

### 4. Add citation to dataset_description.json

In `scripts/build_atlas_pack.py`, update `DATASET_DESCRIPTION["ReferencesAndLinks"]`:

```python
DATASET_DESCRIPTION = {
    ...
    "ReferencesAndLinks": [
        ...,
        "Author et al. YEAR - Journal - https://doi.org/..."
    ]
}
```

### 5. Test

```bash
uv run python main.py

# Verify expected files exist
ls atlases/atlas-<Name>/

# Verify row count matches expected region count
python -c "
import pandas as pd
df = pd.read_csv('atlases/atlas-<Name>/atlas-<Name>_dseg.tsv', sep='\t')
print(f'{len(df)} regions')
print(df.dtypes)
print(df.head())
"
```

### 6. Save

```bash
datalad save -m "Add atlas-<Name>"
```

## BIDS Naming Reference

| Entity | Values | Notes |
|--------|--------|-------|
| `atlas-` | `TianS1`, `HCPex`, `HCPMMP` | CamelCase; no hyphens or spaces |
| `space-` | `MNI152NLin2009cAsym`, `fsLR`, `fsaverage` | Use TemplateFlow names |
| `res-` | `01` (1 mm), `02` (2 mm) | Volumetric only; omit for surface |
| `hemi-` | `L`, `R` | Required for per-hemisphere surface files |
| `_dseg` | — | Suffix for discrete segmentation images |
| `_dseg.tsv` | — | Lookup table; no space/res/hemi entities |

### Valid filename examples

```
# Volumetric
atlas-MyAtlas_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz

# Surface (per-hemisphere)
atlas-MyAtlas_space-fsLR_hemi-L_dseg.label.gii
atlas-MyAtlas_space-fsLR_hemi-R_dseg.label.gii

# Lookup table (no space/res/hemi)
atlas-MyAtlas_dseg.tsv
```

## DataLad Notes

Binary files (NIfTI, GIFTI) are tracked by **git-annex**. The `.gitattributes` file is pre-configured to annex `*.nii.gz` and `*.gii` files automatically.

- Use `datalad save` instead of `git commit` to properly annex new binary files
- Use `datalad get <path>` to download annexed files after cloning
- Use `git annex unlock <path>` before overwriting an annexed file in-place (or let the build scripts overwrite via `shutil.copy`)

```bash
# Full cycle
datalad clone <url>
cd snbb-atlas-pack
datalad get atlases/atlas-TianS1/   # retrieve annexed NIfTI
uv run python main.py               # rebuild
datalad save -m "Update atlases"    # re-annex updated files
```
