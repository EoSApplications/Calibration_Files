# Load libraries
    # Load standard libraries
import json
from pathlib import Path





# Read every calibration YAML file in the parent folder into one name-to-contents map
    # Website_Files/Build/Sync_Pyodide_Packages.py copies the resulting bundle into
    # Pyodide_Packages/, where Pyodide_Bootstrap.js fetches it as a single request
    # and writes each entry back out as an individual file in Pyodide's virtual
    # filesystem - one network round trip instead of one per calibration file
def Build_The_Calibration_File_Contents_Map(Calibration_Files_Folder):
    # Store the raw text of each calibration file, keyed by file name
    Calibration_File_Contents_By_Name = {}
    # Sort the file list so the bundle is always written in the same order
    for Yaml_File_Path in sorted(Calibration_Files_Folder.glob('*.yaml')):
        # Read the file as text - calibration YAML files are plain UTF-8, never binary
        Calibration_File_Contents_By_Name[Yaml_File_Path.name] = Yaml_File_Path.read_text(encoding='utf-8')
    # Return the completed map of file name to file contents
    return Calibration_File_Contents_By_Name


# Write the bundle file used by the website to fetch every calibration file at once
def Write_The_Bundle_File(Calibration_Files_Folder, Output_Folder):
    Calibration_File_Contents_By_Name = Build_The_Calibration_File_Contents_Map(Calibration_Files_Folder)
    # Write the bundle into this script's own folder (Distribution/), not next to the yaml files
    Bundle_File_Path = Output_Folder / 'Calibration_Files_Bundle.json'
    Bundle_File_Path.write_text(
        json.dumps(Calibration_File_Contents_By_Name, indent=2, sort_keys=True), encoding='utf-8',
    )
    print(f'[Calibration Bundle] Wrote {len(Calibration_File_Contents_By_Name)} files to {Bundle_File_Path}')
    # Return the path that was written, in case a caller wants to report or re-stage it
    return Bundle_File_Path


if __name__ == '__main__':
    # This script lives in Distribution/, one level below the calibration YAML files themselves
    Output_Folder = Path(__file__).resolve().parent
    Calibration_Files_Folder = Output_Folder.parent
    Write_The_Bundle_File(Calibration_Files_Folder, Output_Folder)





