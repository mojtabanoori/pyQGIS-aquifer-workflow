"""STEP 3 — Signed thickness raster and diagnostic summary template.
Thickness = bedrock elevation - water-table elevation ONLY when both are
positive-up elevations in the same vertical datum and same units. Negative
estimates are retained and reported for inspection, never silently clipped.
"""
import os
import numpy as np
from osgeo import gdal

# ---- CONFIGURATION: edit to match STEP 2 and your vertical reference ----
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "pyqgis_aquifer_workflow_outputs")
WT_RASTER = os.path.join(OUTPUT_DIR, "WT_tps.tif")
BEDROCK_RASTER = os.path.join(OUTPUT_DIR, "bed_rock_tps.tif")
THICKNESS_RASTER = os.path.join(OUTPUT_DIR, "aquifer_thickness_signed.tif")
VERTICAL_REFERENCE_CONFIRMED = False  # same datum, positive-up elevations, same units
# -------------------------------------------------------------------------
if not VERTICAL_REFERENCE_CONFIRMED:
    raise ValueError("Confirm same vertical datum, positive-up convention, and same units; then set VERTICAL_REFERENCE_CONFIRMED=True.")
wt_ds, br_ds = gdal.Open(WT_RASTER), gdal.Open(BEDROCK_RASTER)
if wt_ds is None or br_ds is None:
    raise FileNotFoundError("Could not open configured elevation rasters; run step 02 and check paths.")
if (wt_ds.RasterXSize, wt_ds.RasterYSize, wt_ds.GetGeoTransform(), wt_ds.GetProjection()) != (br_ds.RasterXSize, br_ds.RasterYSize, br_ds.GetGeoTransform(), br_ds.GetProjection()):
    raise ValueError("Elevation rasters must share dimensions, grid transform, and CRS.")
wt_band, br_band = wt_ds.GetRasterBand(1), br_ds.GetRasterBand(1)
wt, br = wt_band.ReadAsArray().astype(np.float32), br_band.ReadAsArray().astype(np.float32)
wt_nd, br_nd = wt_band.GetNoDataValue(), br_band.GetNoDataValue()
valid = np.isfinite(wt) & np.isfinite(br)
if wt_nd is not None: valid &= wt != wt_nd
if br_nd is not None: valid &= br != br_nd
if not valid.any():
    raise ValueError("No overlapping valid raster cells.")
# Correct convention, conditional on the explicit datum/sign/unit confirmation above.
raw = br - wt
negative = valid & (raw < 0)
result = np.full(raw.shape, -9999.0, dtype=np.float32)
result[valid] = raw[valid]  # preserve signed estimates; no clipping or automatic exclusion
os.makedirs(os.path.dirname(THICKNESS_RASTER) or ".", exist_ok=True)
out = gdal.GetDriverByName("GTiff").Create(THICKNESS_RASTER, wt_ds.RasterXSize, wt_ds.RasterYSize, 1, gdal.GDT_Float32, options=["COMPRESS=LZW"])
if out is None:
    raise RuntimeError("Could not create output raster: %s" % THICKNESS_RASTER)
out.SetGeoTransform(wt_ds.GetGeoTransform()); out.SetProjection(wt_ds.GetProjection())
band = out.GetRasterBand(1); band.SetNoDataValue(-9999); band.WriteArray(result); band.FlushCache(); out.FlushCache(); out = None
values = raw[valid]
print("Signed thickness raster:", THICKNESS_RASTER)
print("Formula: bedrock elevation - water-table elevation (confirmed positive-up, common datum/units).")
print("Valid cells: %d | negative estimates needing inspection: %d (%.2f%%)" % (values.size, int(negative.sum()), 100.0*negative.sum()/values.size))
print("min=%.3f | max=%.3f | mean=%.3f | stddev=%.3f (elevation field units)" % (values.min(), values.max(), values.mean(), values.std()))
print("Negative values may indicate sign/datum/data issues or interpolation artifacts; review inputs and surfaces. They are not automatically invalidated or clipped.")
