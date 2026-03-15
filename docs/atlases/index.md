# Atlas Overview

The SNBB Atlas Pack contains **48 atlas directories** across four atlas families. All outputs are BIDS-structured under `atlases/atlas-<Name>/`.

## BIDS File Naming Conventions

Every atlas directory contains at minimum:

- An **image file** (NIfTI or GIFTI)
- A **`_dseg.tsv` lookup table** with region metadata

File names follow the BIDS atlas entities:

| Entity | Example values | Notes |
|--------|---------------|-------|
| `atlas-` | `TianS1`, `HCPex`, `HCPMMP` | CamelCase, no hyphens |
| `space-` | `MNI152NLin2009cAsym`, `fsLR` | TemplateFlow space names |
| `res-` | `01` (1 mm isotropic) | Volumetric atlases only |
| `hemi-` | `L`, `R` | Per-hemisphere surface files only |
| `_dseg` | — | Suffix for discrete segmentations |
| `_dseg.tsv` | — | Lookup table; no space/res/hemi entities |

**Examples:**

```
atlases/atlas-TianS1/atlas-TianS1_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz
atlases/atlas-TianS1/atlas-TianS1_dseg.tsv
atlases/atlas-HCPMMP/atlas-HCPMMP_space-fsLR_hemi-L_dseg.label.gii
atlases/atlas-HCPMMP/atlas-HCPMMP_space-fsLR_hemi-R_dseg.label.gii
atlases/atlas-HCPMMP/atlas-HCPMMP_dseg.tsv
```

## TSV Lookup Tables

All atlases share a common minimal set of columns:

| Column | Type | Description |
|--------|------|-------------|
| `index` | int | Integer region label in the image (1-based) |
| `label` | str | Short label string (used in software pipelines) |
| `name` | str | Human-readable region name |
| `hemisphere` | str | `L` (left), `R` (right), or blank for bilateral |

Atlas-specific columns (coordinates, lobe, network, color) are documented on each atlas page.

## Atlas Selection Guide

| Use case | Recommended atlas |
|----------|------------------|
| Subcortical-only analysis (tractography, fMRI) | `atlas-TianS1` (coarse) or `atlas-TianS3` (fine) |
| Whole-brain volumetric connectivity matrix | `atlas-Schaefer2018N200n7Tian2020S1` (flexible resolution) or `atlas-HCPex` (HCP-MMP boundaries) |
| Surface-based cortical analysis (Workbench, HCP pipelines) | `atlas-HCPMMP` |
| Comparing with HCP-MMP cortical literature (volumetric) | `atlas-HCPex` |
| Multi-scale or literature-matched cortical parcellation | `atlas-Schaefer2018N{N}n7Tian2020S{S}` (choose N to match prior work) |
| Fine-grained hippocampal / thalamic subdivision | `atlas-TianS3` or `atlas-TianS4` (standalone or combined with Schaefer) |

---

## Summary Table

| Atlas | Regions | Image space | Format | Build module |
|-------|--------:|-------------|--------|--------------|
| [TianS1](tian.md) | 16 | MNI152NLin2009cAsym 1 mm | NIfTI | `atlas_tian.py` |
| [TianS2](tian.md) | 32 | MNI152NLin2009cAsym 1 mm | NIfTI | `atlas_tian.py` |
| [TianS3](tian.md) | 50 | MNI152NLin2009cAsym 1 mm | NIfTI | `atlas_tian.py` |
| [TianS4](tian.md) | 54 | MNI152NLin2009cAsym 1 mm | NIfTI | `atlas_tian.py` |
| [HCPex](hcpex.md) | 426 | MNI152NLin2009cAsym 1 mm | NIfTI | `atlas_hcpex.py` |
| [HCPMMP](hcpmmp.md) | 360 | fsLR 32k | GIFTI (×2) | `atlas_hcpmmp.py` |
| [Schaefer2018+Tian ×40](schaefer_tian.md) | 116–1054 | MNI152NLin2009cAsym 1 mm | NIfTI | `atlas_schaefer_tian.py` |
