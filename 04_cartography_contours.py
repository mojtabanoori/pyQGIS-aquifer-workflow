"""STEP 4 — Cartography and contours template (QGIS Python Console).
Review output units and choose contour interval for the project before running.
"""
import os
from qgis.core import (QgsProject, QgsRasterLayer, QgsColorRampShader,
                       QgsRasterShader, QgsSingleBandPseudoColorRenderer,
                       QgsProcessingFeedback, QgsVectorLayer)
from qgis.PyQt.QtGui import QColor
import processing

# ---- CONFIGURATION: edit for your project ----
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "pyqgis_aquifer_workflow_outputs")
THICKNESS_RASTER = os.path.join(OUTPUT_DIR, "aquifer_thickness_signed.tif")
CONTOUR_INTERVAL = 5.0  # thickness field units; review for scale and intended use
CONTOUR_OUTPUT = os.path.join(OUTPUT_DIR, "aquifer_thickness_contours.gpkg")
# ---------------------------------------------
if not os.path.isfile(THICKNESS_RASTER):
    raise FileNotFoundError("Thickness raster not found; run step 03 and check configured path.")
if CONTOUR_INTERVAL <= 0:
    raise ValueError("CONTOUR_INTERVAL must be positive.")
project = QgsProject.instance()
layer = QgsRasterLayer(THICKNESS_RASTER, "Signed aquifer thickness (review units)")
if not layer.isValid():
    raise RuntimeError("Could not load configured thickness raster.")
shader = QgsColorRampShader(); shader.setColorRampType(QgsColorRampShader.Interpolated)
colors = [QColor("#2c7bb6"), QColor("#abd9e9"), QColor("#ffffbf"), QColor("#fdae61"), QColor("#d7191c")]
items = [QgsColorRampShader.ColorRampItem(v, c, str(v)) for v, c in zip([-50, 0, 50, 100, 150], colors)]
shader.setColorRampItemList(items)
ramp = QgsRasterShader(); ramp.setRasterShaderFunction(shader)
renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, ramp)
renderer.setClassificationMin(-50); renderer.setClassificationMax(150); layer.setRenderer(renderer)
project.addMapLayer(layer)
try:
    result = processing.run("gdal:contour", {"INPUT": THICKNESS_RASTER, "BAND": 1,
        "INTERVAL": CONTOUR_INTERVAL, "FIELD_NAME": "THICKNESS", "CREATE_3D": False,
        "IGNORE_NODATA": True, "NODATA": None, "OFFSET": 0, "EXTRA": "",
        "OUTPUT": CONTOUR_OUTPUT}, feedback=QgsProcessingFeedback())
except Exception as exc:
    raise RuntimeError("Contour processing failed; confirm QGIS Processing/GDAL availability and parameters. %s" % exc)
contours = QgsVectorLayer(CONTOUR_OUTPUT, "Thickness contours (configured interval)", "ogr")
if contours.isValid():
    project.addMapLayer(contours)
else:
    print("Contour output was not loaded as a valid vector layer; inspect processing output:", result)
print("Styled signed raster:", THICKNESS_RASTER)
print("Contour output:", CONTOUR_OUTPUT)
print("Cartography is illustrative. Verify rendering, contour values/units, and negative estimates before interpretation.")
