"""
Visualization script for SNBB Atlas Pack using yabplot.

Generates cortical and/or subcortical plots for:
  - atlas-TianS1 through atlas-TianS4          (subcortical)
  - atlas-HCPex                                 (cortical + subcortical)
  - atlas-HCPMMP                                (cortical, fsLR 32k)
  - atlas-Schaefer2018N{N}n7Tian2020S{S}        (cortical + subcortical)

Outputs PNG files to atlases/<atlas-name>/figures/.
Intermediate mesh/vertex data is cached in derivatives/yabplot/<atlas-name>/.
Schaefer-Tian subcortical reuses the precomputed Tian meshes.
"""

import os
import numpy as np
import pandas as pd
import nibabel as nib
import yabplot as yab
from pathlib import Path

# Force off-screen rendering (no display required).
# yabplot creates plotters with off_screen=False by default (unless display_type='object'),
# so we patch setup_plotter in the scene module AND in the plotting module
# (which imports it by name).
import yabplot.scene as _yab_scene
import yabplot.plotting as _yab_plotting

_orig_setup_plotter = _yab_scene.setup_plotter


def _offscreen_setup_plotter(
    sel_views, layout, figsize, display_type, needs_bottom_row=True
):
    plotter, ncols, nrows = _orig_setup_plotter(
        sel_views, layout, figsize, "object", needs_bottom_row
    )
    return plotter, ncols, nrows


_yab_scene.setup_plotter = _offscreen_setup_plotter
_yab_plotting.setup_plotter = _offscreen_setup_plotter


# Also patch finalize_plot so that display_type='none' takes a screenshot properly:
# when off_screen=True, the plotter renders upon render() not show().
_orig_finalize = _yab_scene.finalize_plot


def _patched_finalize(plotter, export_path, display_type):
    plotter.render()
    if export_path:
        plotter.screenshot(export_path, transparent_background=True)
    plotter.close()
    return None


_yab_scene.finalize_plot = _patched_finalize
_yab_plotting.finalize_plot = _patched_finalize

ATLAS_DIR = Path("atlases")
DERIV_DIR = Path("derivatives/yabplot")
VIEWS_SUBCORTICAL = None  # all views
VIEWS_CORTICAL = None  # all views

# Standard 7-network RGB colors for Schaefer cortical wb_txt generation
_SCHAEFER_NETWORK_RGB = {
    "Vis": (70, 130, 180),
    "SomMot": (60, 179, 113),
    "DorsAttn": (255, 140, 0),
    "SalVentAttn": (238, 130, 238),
    "Limbic": (205, 205, 0),
    "Cont": (220, 20, 60),
    "Default": (148, 103, 189),
}


def _fig_dir(atlas_name: str) -> Path:
    d = ATLAS_DIR / atlas_name / "figures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _plot_subcortical(mesh_dir: Path, out_path: str) -> None:
    yab.plot_subcortical(
        data=None,
        custom_atlas_path=str(mesh_dir),
        legend=False,
        views=VIEWS_SUBCORTICAL,
        figsize=(2000, 700),
        bmesh_type="midthickness",
        bmesh_alpha=0.08,
        nan_alpha=0.0,
        display_type="none",
        export_path=out_path,
    )


def _plot_cortical(atlas_dir: Path, out_path: str) -> None:
    yab.plot_cortical(
        data=None,
        custom_atlas_path=str(atlas_dir),
        views=VIEWS_CORTICAL,
        figsize=(2000, 800),
        display_type="none",
        export_path=out_path,
    )


def _build_subcortical_meshes(
    nii_path: Path, labels_dict: dict, mesh_dir: Path
) -> None:
    if mesh_dir.exists() and any(mesh_dir.glob("*.vtk")):
        print(f"  Skipping mesh build (already exists): {mesh_dir}")
        return
    yab.build_subcortical_atlas(str(nii_path), labels_dict, str(mesh_dir))


# ---------------------------------------------------------------------------
# Tian subcortical atlases (S1–S4)
# ---------------------------------------------------------------------------


def build_and_plot_tian(scale: int) -> None:
    name = f"atlas-TianS{scale}"
    nii_path = ATLAS_DIR / name / f"{name}_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz"
    tsv_path = ATLAS_DIR / name / f"{name}_dseg.tsv"
    mesh_dir = DERIV_DIR / name
    fig_dir = _fig_dir(name)

    df = pd.read_csv(tsv_path, sep="\t")
    labels_dict = dict(zip(df["index"].astype(int), df["label"]))

    print(f"\n=== {name}: subcortical ===")
    _build_subcortical_meshes(nii_path, labels_dict, mesh_dir)

    out_path = str(fig_dir / f"{name}_subcortical.png")
    print(f"  Plotting → {out_path}")
    _plot_subcortical(mesh_dir, out_path)
    print(f"  Saved: {out_path}")


# ---------------------------------------------------------------------------
# HCPex atlas — cortical (volumetric → surface) + subcortical meshes
# ---------------------------------------------------------------------------


def _write_wb_label_txt(df: pd.DataFrame, out_path: Path) -> None:
    """Write Connectome Workbench -volume-label-import label list format.

    Format (two lines per region):
        <label_name>
        <key> <R 0-255> <G 0-255> <B 0-255> <alpha 0-255>
    """
    with open(out_path, "w") as f:
        for _, row in df.iterrows():
            f.write(f"{row['label']}\n")
            f.write(
                f"{int(row['index'])} {int(row['r'])} {int(row['g'])} {int(row['b'])} 255\n"
            )


def _build_cortical_atlas(
    nii_path: Path,
    wb_df: pd.DataFrame,
    atlas_dir: Path,
    atlasname: str,
    exclude_list: list[str] | None = None,
) -> None:
    csv_out = atlas_dir / f"{atlasname}.csv"
    if csv_out.exists():
        print(f"  Skipping cortical atlas build (already exists): {atlas_dir}")
        return
    wb_txt_path = Path(f"/tmp/{atlasname}_wb_labels.txt")
    _write_wb_label_txt(wb_df, wb_txt_path)
    yab.build_cortical_atlas(
        str(nii_path),
        str(wb_txt_path),
        str(atlas_dir),
        atlasname=atlasname,
        exclude_list=exclude_list,
    )


def build_and_plot_hcpex() -> None:
    name = "atlas-HCPex"
    nii_path = ATLAS_DIR / name / f"{name}_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz"
    tsv_path = ATLAS_DIR / name / f"{name}_dseg.tsv"
    atlas_dir = DERIV_DIR / name
    fig_dir = _fig_dir(name)
    atlas_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(tsv_path, sep="\t")
    df_cortical = df[df["lobe"].notna()].copy()
    df_subcortical = df[df["lobe"].isna()].copy()

    # Cortical
    print(f"\n=== {name}: cortical ({len(df_cortical)} regions) ===")
    _build_cortical_atlas(nii_path, df_cortical, atlas_dir, atlasname="HCPex")
    out_cortical = str(fig_dir / f"{name}_cortical.png")
    print(f"  Plotting → {out_cortical}")
    _plot_cortical(atlas_dir, out_cortical)
    print(f"  Saved: {out_cortical}")

    # Subcortical
    print(f"\n=== {name}: subcortical ({len(df_subcortical)} regions) ===")
    mesh_dir = atlas_dir / "subcortical"
    labels_dict = dict(
        zip(df_subcortical["index"].astype(int), df_subcortical["label"])
    )
    _build_subcortical_meshes(nii_path, labels_dict, mesh_dir)
    out_subcortical = str(fig_dir / f"{name}_subcortical.png")
    print(f"  Plotting → {out_subcortical}")
    _plot_subcortical(mesh_dir, out_subcortical)
    print(f"  Saved: {out_subcortical}")


# ---------------------------------------------------------------------------
# HCPMMP surface atlas (fsLR 32k GIFTI → CSV + LUT for yabplot)
# ---------------------------------------------------------------------------


def _gifti_labels(img) -> dict[int, tuple[str, tuple[int, int, int]]]:
    """Return {key: (name, (r, g, b))} from a GIFTI label table."""
    result = {}
    for lbl in img.labeltable.labels:
        if lbl.key == 0 or lbl.label in ("???", ""):
            continue
        r = int(round(lbl.red * 255))
        g = int(round(lbl.green * 255))
        b = int(round(lbl.blue * 255))
        result[lbl.key] = (lbl.label, (r, g, b))
    return result


def build_and_plot_hcpmmp() -> None:
    name = "atlas-HCPMMP"
    lh_gii_path = ATLAS_DIR / name / f"{name}_space-fsLR_hemi-L_dseg.label.gii"
    rh_gii_path = ATLAS_DIR / name / f"{name}_space-fsLR_hemi-R_dseg.label.gii"
    atlas_dir = DERIV_DIR / name
    fig_dir = _fig_dir(name)
    atlas_dir.mkdir(parents=True, exist_ok=True)

    csv_path = atlas_dir / "HCPMMP.csv"
    lut_path = atlas_dir / "HCPMMP.txt"

    if not csv_path.exists():
        lh_img = nib.load(str(lh_gii_path))
        rh_img = nib.load(str(rh_gii_path))

        lh_data = lh_img.darrays[0].data.astype(int)  # (32492,)
        rh_data = rh_img.darrays[0].data.astype(int)  # (32492,)

        lh_labels = _gifti_labels(lh_img)
        rh_labels = _gifti_labels(rh_img)

        # Remap RH keys to a non-overlapping range above all LH keys
        lh_max = max(lh_labels.keys()) if lh_labels else 0
        rh_data_remapped = np.where(rh_data == 0, 0, rh_data + lh_max)

        # Combined vertex array (LH then RH, 64984 total)
        combined = np.concatenate([lh_data, rh_data_remapped])
        np.savetxt(str(csv_path), combined, fmt="%i")

        # Build LUT: id  name  r  g  b
        with open(lut_path, "w") as f:
            for key, (lbl_name, (r, g, b)) in sorted(lh_labels.items()):
                f.write(f"{key}  {lbl_name}  {r}  {g}  {b}\n")
            for key, (lbl_name, (r, g, b)) in sorted(rh_labels.items()):
                f.write(f"{key + lh_max}  {lbl_name}  {r}  {g}  {b}\n")
    else:
        print("  Skipping HCPMMP CSV/LUT build (already exists)")

    out_path = str(fig_dir / f"{name}_cortical.png")
    print(f"\n=== {name}: cortical (fsLR 32k) ===")
    print(f"  Plotting → {out_path}")
    _plot_cortical(atlas_dir, out_path)
    print(f"  Saved: {out_path}")


# ---------------------------------------------------------------------------
# Schaefer-Tian combination atlases
# ---------------------------------------------------------------------------


def _schaefer_wb_df(df_cortical: pd.DataFrame) -> pd.DataFrame:
    """Add r/g/b columns to Schaefer cortical rows using 7-network colors."""
    df = df_cortical.copy()
    default_rgb = (128, 128, 128)
    df["r"] = df["network"].map(lambda n: _SCHAEFER_NETWORK_RGB.get(n, default_rgb)[0])
    df["g"] = df["network"].map(lambda n: _SCHAEFER_NETWORK_RGB.get(n, default_rgb)[1])
    df["b"] = df["network"].map(lambda n: _SCHAEFER_NETWORK_RGB.get(n, default_rgb)[2])
    return df


def build_and_plot_schaefer_tian(n_regions: int, scale: int) -> None:
    name = f"atlas-Schaefer2018N{n_regions}n7Tian2020S{scale}"
    nii_path = ATLAS_DIR / name / f"{name}_space-MNI152NLin2009cAsym_res-01_dseg.nii.gz"
    tsv_path = ATLAS_DIR / name / f"{name}_dseg.tsv"
    atlas_dir = DERIV_DIR / name
    fig_dir = _fig_dir(name)
    atlas_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(tsv_path, sep="\t")
    df_cortical = df[df["component"] == "cortex"].copy()

    atlasname = f"Schaefer2018N{n_regions}n7"

    # Cortical
    print(f"\n=== {name}: cortical ({len(df_cortical)} regions) ===")
    wb_df = _schaefer_wb_df(df_cortical)
    # exclude_list=['LABEL_'] drops auto-labeled subcortical voxels that wb_command
    # assigns when NIfTI indices aren't listed in the wb_txt (the combined atlas NIfTI
    # includes subcortical indices that we intentionally omit from the wb label file)
    _build_cortical_atlas(
        nii_path, wb_df, atlas_dir, atlasname=atlasname, exclude_list=["LABEL_"]
    )
    out_cortical = str(fig_dir / f"{name}_cortical.png")
    print(f"  Plotting → {out_cortical}")
    _plot_cortical(atlas_dir, out_cortical)
    print(f"  Saved: {out_cortical}")

    # Subcortical — reuse precomputed Tian S{scale} meshes
    tian_mesh_dir = DERIV_DIR / f"atlas-TianS{scale}"
    print(f"\n=== {name}: subcortical (reusing atlas-TianS{scale} meshes) ===")
    out_subcortical = str(fig_dir / f"{name}_subcortical.png")
    print(f"  Plotting → {out_subcortical}")
    _plot_subcortical(tian_mesh_dir, out_subcortical)
    print(f"  Saved: {out_subcortical}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

SCHAEFER_N = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
SCHAEFER_S = [1, 2, 3, 4]


def visualize_all() -> None:
    # Tian standalone subcortical atlases
    for scale in [1, 2, 3, 4]:
        build_and_plot_tian(scale)

    # HCPex cortical + subcortical
    build_and_plot_hcpex()

    # HCPMMP cortical (fsLR 32k surface)
    build_and_plot_hcpmmp()

    # Schaefer-Tian combinations
    for n in SCHAEFER_N:
        for s in SCHAEFER_S:
            build_and_plot_schaefer_tian(n, s)
    print("\nAll atlas visualizations complete.")


if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    visualize_all()
