# Calibration_Files

This repository contains all calibration files that are used in all EoSApplications products. All applications check this repository for changes when looking for calibration file updates. 


## Contents

- **`*.yaml`** are files for every pressure calibration that have been digitized from their corresponding source papers
- **`Distribution/`** contains files EoSApplications products look at when either fetching or updating calibration file contents


## Naming convention

`Author(s), Year_Composition[_variant].yaml`
- This matching how the source study would normally be cited (e.g. `Akahama and Kawamura 2004.yaml`, `Dewaele et al., 2004_Al.yaml`)
- When one study reports more than one calibration (different pressure media, fixed vs. free parameters, etc.), a short variant suffix distinguishes them (e.g. `_k0fixed`, `_BM`, `_vin`)


## What's in a calibration file

Each file records, at minimum: the source study, composition, measurement method/technique, the equation-of-state fit and its parameters with uncertainties, the pressure scale(s) it was cross-calibrated against, and bibliographic/provenance metadata (DOI, synchrotron facility, notes on data quality or caveats). See any existing file for the exact field set, or `EoS_Math/Load_Calibration_Files.py` in the `EoSAlign` repo for how each field is parsed.


## Attribution

No additional copyright is claimed over the data compiled in this repository. Every calibration's actual values belong to its cited source study. This repository digitized published values into a common format for use with the EoSApplications software suite. If you use a specific calibration in your own work, cite that calibration's original paper (see its `study`/`doi` fields).




