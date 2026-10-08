# PyQGIS Aquifer Mapping Workflow (Four-Step Template)

A four-script **starting-point template** for diagnostic point QC, separate surface interpolation, signed thickness derivation, and cartographic output using QGIS. It is not a validated hydrogeological method, a turnkey model, or evidence of scientific accuracy. **No scientific validation or QGIS runtime testing is claimed.** Review all inputs, configuration, intermediate products, and outputs with a qualified domain expert.

> **Critical sign convention:** Thickness may be computed as `bedrock elevation - water-table elevation` **only if** both values are elevations in the same vertical datum, use a positive-up convention, and use compatible units. An earlier script shown in the user's screenshot used `WT - bedrock`; that reversed subtraction can reverse the thickness sign. Confirm the actual meaning and convention of each source field before enabling thickness calculations. If values are depths below a reference surface, mixed datums, or otherwise not comparable elevations, this formula is not valid as written.

## What this repository contains

| File | Stage | Role |
|---|---|---|
| `01_data_qc_filter.py` | 1 — QC | Prints diagnostic nearest-point distances and, only after explicit vertical-reference confirmation, flags point-derived thickness values. Does not edit or exclude data. |
| `02_tps_interpolation.py` | 2 — Interpolation | Uses SciPy's thin-plate-spline radial basis function to create independent WT and bedrock GeoTIFF surfaces, masked to a polygon. |
| `03_thickness_analysis.py` | 3 — Thickness | Derives signed `bedrock - WT` raster and reports negative estimates for inspection; it does not clip them. |
| `04_cartography_contours.py` | 4 — Cartography | Loads/styles the signed raster and requests contours via QGIS Processing/GDAL. |
| `requirements.txt` | Dependencies | Lists SciPy and NumPy for the interpolation script. |
| `.gitignore` | Git hygiene | Excludes common local outputs and temporary files. |

The QC and interpolation steps are deliberately separate. Nearest-neighbor thresholds and thickness-range flags are **diagnostic prompts, not automatic exclusions**. They must be selected for the actual study and reviewed against source records. Interpolation and thickness outputs are not uncertainty estimates.

## Important configuration — do this before running

Each script has a `CONFIGURATION` section near its beginning. Edit and verify, at minimum:

- exact QGIS layer names and field names (the defaults are examples, not guaranteed to match your project);
- the actual field meaning, numeric type, missing-value conventions, vertical datum, positive-up/down sign convention, and vertical units;
- a suitable projected CRS, coordinate system, map units, and matching CRS for inputs;
- study extent and polygon geometry (the interpolation defaults to the clip boundary's bounding extent; `USER_EXTENT` is available to set a deliberate extent);
- grid resolution in the CRS's map units and the output directory;
- nearest-distance and thickness QC thresholds, in explicitly verified units;
- contour interval and display range to suit the thickness units and map purpose.

The scripts fail closed on key unconfirmed assumptions: set `CRS_AND_UNITS_VERIFIED = True` in step 2 only after checking the CRS and map units; set `VERTICAL_REFERENCE_CONFIRMED = True` in steps 1 and 3 only after confirming same-datum, positive-up elevations and compatible vertical units. Do not set these flags merely to bypass an error. The scripts cannot determine whether your source data meet these scientific assumptions.

Step 1 assumes a single point layer contains both configured elevation fields. Adapt its configuration/code if your observations live in separate layers. Step 2 likewise interpolates those two fields from that configured point layer. Inspect duplicate, collinear, sparse, clustered, and invalid points; SciPy TPS may overshoot, especially near edges. User-specified extent, grid size, clip mask, and coordinate units matter.

### Negative estimates and flags

Negative thickness estimates are retained in the signed output and reported as possible artifacts or invalid/mismatched inputs for inspection. They can arise from interpolation behavior, input data, sign convention, or datum/unit problems. **Do not use negative clipping as a scientific fix without review.** The QC range and nearest-distance flags do not automatically drop records; investigate and document any decision to exclude or transform observations. The screenshot's earlier `WT - bedrock` calculation may reverse the sign; verify before proceeding.

## Requirements and execution environment

- QGIS 3.x and its **QGIS Python Console** (PyQGIS and Qt APIs are supplied by the QGIS installation).
- QGIS Processing enabled, with its GDAL provider/contour algorithm available; GDAL Python bindings compatible with the installed QGIS environment.
- NumPy and SciPy available to the Python environment used by QGIS. `requirements.txt` lists `numpy` and `scipy`; installing packages into an unrelated system Python does not make them available to QGIS. QGIS distributions may already include them. Use the package manager/environment guidance for your QGIS distribution; do not replace its GDAL/QGIS packages casually with system pip packages.

These scripts are intended to be run **inside the QGIS Python Console**, not as ordinary standalone Python scripts. They were syntax-checked as Python source only; they have not been executed in QGIS here. API/provider availability can vary across QGIS/GDAL versions.

## Run (first test on copies)

1. Make a copy of your QGIS project and data. Work on copies first; do not let a template overwrite source data. Verify layer names, field names, geometry types, CRS, extent, coordinate units, vertical datum/sign/units, and missing values.
2. Edit each script's configuration section and inspect the code. Confirm that the configured output directory is suitable and writable.
3. Open the copied project in QGIS. Open **Plugins → Python Console** (menu wording can vary).
4. Run the four scripts in order. In the console, use this pattern, replacing the path for each script:

   ```python
   exec(open(r"/absolute/path/to/pyqgis-aquifer-workflow/01_data_qc_filter.py", encoding="utf-8").read())
   ```

   Then run `02_tps_interpolation.py`, `03_thickness_analysis.py`, and `04_cartography_contours.py` in order in the same way. Review each console message and output before continuing.
5. By default, outputs are written under `~/pyqgis_aquifer_workflow_outputs/`. Check the generated rasters' CRS, transform, resolution, NoData mask, extent, and values; inspect negative thickness estimates and contours. The scripts do not replace visual, statistical, field, or scientific review.

No real input data are included. Do not add confidential coordinates, measurements, credentials, QGIS project files containing sensitive paths/data, or generated results to a public repository without authorization. `.gitignore` is a safeguard, not a guarantee; inspect staged files before every commit.

## GitHub setup and basic workflow

1. Sign in to GitHub and create a **new empty repository**. Choose a repository name such as `pyqgis-aquifer-workflow`. Do not initialize it with another README if pushing this existing project.
2. Install Git. Open a terminal in this project folder and review `git status` and the file list. Initialize and commit the template:

   ```bash
   git init
   git add README.md LICENSE .gitignore requirements.txt 01_data_qc_filter.py 02_tps_interpolation.py 03_thickness_analysis.py 04_cartography_contours.py
   git status
   git commit -m "Add four-step PyQGIS aquifer workflow template"
   git branch -M main
   git remote add origin https://github.com/<YOUR-USERNAME>/<REPOSITORY-NAME>.git
   git push -u origin main
   ```

   Replace the placeholders with your own account/repository. GitHub may request browser authentication or a token; never place passwords or tokens in a script or commit.
3. For later changes: edit files, run `git status`, inspect the changes (`git diff`), then `git add <files>`, `git commit -m "Describe the change"`, and `git push`. `git status` helps identify staged/untracked files but does not itself prove data are safe to publish.
4. Alternatively, use GitHub's web UI to create the repository and upload the reviewed project files. The ZIP archive is for convenience; do not upload sensitive or unintended files.

Git is version control (tracks project changes); GitHub hosts and shares repositories. Public visibility means anyone can view and copy the repository. Keep a repository private if needed, and follow your data license/permissions.

## License and attribution

See [`LICENSE`](LICENSE). Cite source data and relevant QGIS, GDAL, NumPy, SciPy versions and interpolation choices in downstream work. Data rights remain with their owners. No results, accuracy, or scientific suitability are warranted by this template.
