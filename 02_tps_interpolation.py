"""STEP 2 — Thin-plate-spline surface template (QGIS Python Console).
Review and edit CONFIGURATION; this script is not scientifically validated.
"""
import os
import numpy as np
from scipy.interpolate import Rbf
from osgeo import gdal, osr
from qgis.core import QgsProject, QgsGeometry, QgsPointXY, QgsWkbTypes

# ---- CONFIGURATION: edit for your project ----
POINT_LAYER_NAME = "sounding-wt"
CLIP_LAYER_NAME = "aquifer_azghand_1"
WT_FIELD = "WT"
BEDROCK_FIELD = "bed-rock"
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "pyqgis_aquifer_workflow_outputs")
GRID_RESOLUTION = 100.0  # CRS map units; verify desired ground resolution and units
USER_EXTENT = None        # Optional (xmin, xmax, ymin, ymax) in the input CRS; None = clip boundary bounds
CRS_AND_UNITS_VERIFIED = False  # Set True only after verifying projected CRS, units, and suitability
# ---------------------------------------------

def require_one(name):
    matches = QgsProject.instance().mapLayersByName(name)
    if len(matches) != 1:
        raise ValueError("Expected exactly one layer named %r; found %d" % (name, len(matches)))
    return matches[0]

points, clip = require_one(POINT_LAYER_NAME), require_one(CLIP_LAYER_NAME)
if not CRS_AND_UNITS_VERIFIED:
    raise ValueError("Review CONFIGURATION and verify suitable projected CRS and coordinate units, then set CRS_AND_UNITS_VERIFIED=True.")
if not points.crs().isValid():
    raise ValueError("Input point layer CRS is invalid; assign/verify the correct CRS first.")
if points.crs().isGeographic():
    raise ValueError("Interpolation requires a suitable projected CRS, not a geographic CRS.")
if points.crs() != clip.crs():
    raise ValueError("Point and clip layer CRS must match; reproject deliberately before use.")
if QgsWkbTypes.geometryType(points.wkbType()) != QgsWkbTypes.PointGeometry:
    raise ValueError("Configured observation layer is not a point layer.")
if QgsWkbTypes.geometryType(clip.wkbType()) != QgsWkbTypes.PolygonGeometry:
    raise ValueError("Configured clip layer is not a polygon layer.")
fields = [WT_FIELD, BEDROCK_FIELD]
missing = [n for n in fields if points.fields().indexFromName(n) < 0]
if missing:
    raise ValueError("Missing configured field(s) %s in %r." % (missing, POINT_LAYER_NAME))
if not np.isfinite(GRID_RESOLUTION) or GRID_RESOLUTION <= 0:
    raise ValueError("GRID_RESOLUTION must be a finite, positive value in CRS map units.")
features = []
for f in points.getFeatures():
    g = f.geometry()
    if g is None or g.isNull() or g.isEmpty() or QgsWkbTypes.isMultiType(g.wkbType()):
        continue
    try:
        vals = [float(f[n]) for n in fields]
        xy = g.asPoint()
    except (TypeError, ValueError):
        continue
    if not all(np.isfinite(v) for v in vals):
        continue
    features.append((xy.x(), xy.y(), vals))
if len(features) < 3:
    raise ValueError("At least three usable complete points are required; verify inputs and fields.")
clip_geoms = [f.geometry() for f in clip.getFeatures() if f.geometry() and not f.geometry().isEmpty()]
if not clip_geoms:
    raise ValueError("Clip layer has no usable geometries.")
geom = QgsGeometry.unaryUnion(clip_geoms)
if geom.isNull() or geom.isEmpty():
    raise ValueError("Could not build clip geometry.")
extent = geom.boundingBox()
if USER_EXTENT is not None:
    if len(USER_EXTENT) != 4:
        raise ValueError("USER_EXTENT must be (xmin, xmax, ymin, ymax).")
    xmin, xmax, ymin, ymax = map(float, USER_EXTENT)
else:
    xmin, xmax, ymin, ymax = extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum()
if not all(np.isfinite(v) for v in (xmin, xmax, ymin, ymax)) or xmax <= xmin or ymax <= ymin:
    raise ValueError("Configured interpolation extent is invalid.")
nx, ny = int(np.ceil((xmax-xmin)/GRID_RESOLUTION)), int(np.ceil((ymax-ymin)/GRID_RESOLUTION))
if nx < 1 or ny < 1 or nx*ny > 100000000:
    raise ValueError("Grid dimensions invalid or exceed safety limit; verify extent and resolution.")
xs = xmin + (np.arange(nx)+0.5)*GRID_RESOLUTION
yvals = ymax - (np.arange(ny)+0.5)*GRID_RESOLUTION
grid_x, grid_y = np.meshgrid(xs, yvals)
inside = np.zeros((ny, nx), dtype=bool)
for row, y in enumerate(yvals):
    for col, x in enumerate(xs):
        inside[row, col] = geom.intersects(QgsGeometry.fromPointXY(QgsPointXY(float(x), float(y))))
if not inside.any():
    raise ValueError("Grid has no cell centers inside clip geometry; review extent/resolution.")
os.makedirs(OUTPUT_DIR, exist_ok=True)
srs = osr.SpatialReference()
if srs.ImportFromWkt(points.crs().toWkt()) != 0:
    raise ValueError("Could not transfer input CRS to raster.")
coords = np.asarray([[x, y] for x, y, _ in features], dtype=float)
for field_index, name in enumerate(fields):
    values = np.asarray([row[2][field_index] for row in features], dtype=float)
    if len(np.unique(coords, axis=0)) < 3:
        raise ValueError("Fewer than three distinct point coordinates; review duplicates.")
    print("Interpolating %s from %d observations to %d x %d cells." % (name, len(values), nx, ny))
    try:
        rbf = Rbf(coords[:,0], coords[:,1], values, function="thin_plate")
        surface = rbf(grid_x[inside], grid_y[inside])
    except Exception as exc:
        raise RuntimeError("TPS failed for %s; inspect duplicate/collinear points and data. %s" % (name, exc))
    arr = np.full((ny, nx), -9999.0, dtype=np.float32)
    arr[inside] = np.asarray(surface, dtype=np.float32)
    path = os.path.join(OUTPUT_DIR, name.replace('-', '_') + "_tps.tif")
    ds = gdal.GetDriverByName("GTiff").Create(path, nx, ny, 1, gdal.GDT_Float32, options=["COMPRESS=LZW"])
    if ds is None:
        raise RuntimeError("Could not create raster: %s" % path)
    ds.SetGeoTransform((xmin, GRID_RESOLUTION, 0, ymax, 0, -GRID_RESOLUTION))
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1); band.SetNoDataValue(-9999); band.WriteArray(arr); band.FlushCache()
    ds.FlushCache(); ds = None
    print("Saved:", path)
print("Interpolation complete. Inspect support, edge behavior, units, and artifacts; no scientific validation is implied.")
