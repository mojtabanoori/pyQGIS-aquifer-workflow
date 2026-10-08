"""STEP 1 — Diagnostic point QC template (run in the QGIS Python Console).

QC flags are observations for review, NOT automatic exclusions. Configure every
item in CONFIGURATION before use. No scientific validation is implied.
"""
from math import hypot, isfinite
from qgis.core import QgsProject, QgsSpatialIndex, QgsWkbTypes

# ---- CONFIGURATION: edit for your project ----
POINT_LAYER_NAME = "sounding-wt"
WT_FIELD = "WT"
BEDROCK_FIELD = "bed-rock"
NEAREST_DISTANCE_THRESHOLD = 500.0  # layer map units; set deliberately
THICKNESS_MIN_FLAG = 10.0           # field units; diagnostic only
THICKNESS_MAX_FLAG = 160.0          # field units; diagnostic only
VERTICAL_REFERENCE_CONFIRMED = False  # same vertical datum, positive-up, same units
# ---------------------------------------------

def require_layer(name):
    matches = QgsProject.instance().mapLayersByName(name)
    if len(matches) != 1:
        raise ValueError("Expected exactly one project layer named %r; found %d" % (name, len(matches)))
    return matches[0]

def numeric(value):
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None

points = require_layer(POINT_LAYER_NAME)
if QgsWkbTypes.geometryType(points.wkbType()) != QgsWkbTypes.PointGeometry:
    raise ValueError("Configured point layer is not a point geometry layer.")
missing = [name for name in (WT_FIELD, BEDROCK_FIELD) if points.fields().indexFromName(name) < 0]
if missing:
    raise ValueError("Missing configured field(s) %s in layer %r." % (missing, POINT_LAYER_NAME))
if NEAREST_DISTANCE_THRESHOLD <= 0:
    raise ValueError("NEAREST_DISTANCE_THRESHOLD must be positive and in the layer CRS units.")

valid = {}
invalid_geometry = []
for f in points.getFeatures():
    g = f.geometry()
    if g is None or g.isNull() or g.isEmpty() or QgsWkbTypes.isMultiType(g.wkbType()):
        invalid_geometry.append(f.id())
        continue
    try:
        pt = g.asPoint()
        valid[f.id()] = (pt, f)
    except Exception:
        invalid_geometry.append(f.id())
index = QgsSpatialIndex()
for fid, (pt, _) in valid.items():
    # Insert feature-like object through its original feature geometry.
    index.addFeature(valid[fid][1])

print("QC report (diagnostic only): feature_id | nearest distance (layer units) | thickness | flags")
flagged = 0
for fid, (pt, f) in valid.items():
    nearest = index.nearestNeighbor(pt, 2)
    other = next((candidate for candidate in nearest if candidate != fid), None)
    distance = hypot(pt.x() - valid[other][0].x(), pt.y() - valid[other][0].y()) if other is not None else None
    flags = []
    if other is not None and distance < NEAREST_DISTANCE_THRESHOLD:
        flags.append("NEARER THAN CONFIGURED THRESHOLD")
    elif other is None:
        flags.append("NO OTHER POINT")
    wt, br = numeric(f[WT_FIELD]), numeric(f[BEDROCK_FIELD])
    thickness = None
    if wt is None or br is None:
        flags.append("MISSING/NON-NUMERIC ELEVATION")
    elif VERTICAL_REFERENCE_CONFIRMED:
        # Valid only for same vertical datum, positive-up elevations, and same units.
        thickness = br - wt
        if thickness < 0:
            flags.append("NEGATIVE THICKNESS: inspect elevations/sign/data; not excluded")
        if thickness == 0:
            flags.append("ZERO THICKNESS: inspect; not excluded")
        if thickness < THICKNESS_MIN_FLAG or thickness > THICKNESS_MAX_FLAG:
            flags.append("OUTSIDE CONFIGURED THICKNESS RANGE: inspect; not excluded")
    else:
        flags.append("THICKNESS NOT CALCULATED: confirm vertical reference and enable config")
    if flags:
        flagged += 1
        print("%s | %s | %s | %s" % (fid, "%.3f" % distance if distance is not None else "n/a", "%.3f" % thickness if thickness is not None else "n/a", "; ".join(flags)))
print("Checked %d usable point(s); flagged %d; invalid/unsupported geometries: %s." % (len(valid), flagged, invalid_geometry))
print("Thresholds are diagnostic only; review source records before any exclusion.")
