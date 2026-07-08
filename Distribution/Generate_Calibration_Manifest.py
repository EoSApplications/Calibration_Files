# Load libraries
    # Load standard libraries
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path





# Normalize text line endings before hashing so the manifest is identical on every platform
def Normalize_Calibration_File_Bytes(File_Bytes):
    return File_Bytes.replace(b'\r\n', b'\n').replace(b'\r', b'\n')



# Walk every calibration YAML file in the parent folder and hash its contents
def Build_The_File_Hash_Map(Calibration_Files_Folder):
    # Store one SHA-256 hash per calibration file, keyed by file name
    File_Hash_Map = {}
    # Sort the file list so the manifest is always written in the same order
    for Yaml_File_Path in sorted(Calibration_Files_Folder.glob('*.yaml')):
        # Hash canonical LF bytes so Windows and Unix checkouts produce the same manifest
        File_Bytes = Normalize_Calibration_File_Bytes(Yaml_File_Path.read_bytes())
        File_Hash = hashlib.sha256(File_Bytes).hexdigest()
        # Store the hash under the file's name
        File_Hash_Map[Yaml_File_Path.name] = f'sha256:{File_Hash}'
    # Return the completed map of file name to hash
    return File_Hash_Map


# Write the manifest file used by applications and the website to detect changes
def Write_The_Manifest_File(Calibration_Files_Folder, Output_Folder):
    File_Hash_Map = Build_The_File_Hash_Map(Calibration_Files_Folder)
    # Record the generation time in UTC so it is unambiguous regardless of time zone
    Generated_Timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    # Assemble the manifest dictionary in the documented index.json format
    Manifest_Data = {
        'Generated': Generated_Timestamp,
        'Files': File_Hash_Map,
    }
    # Write the manifest into this script's own folder (Distribution/), not next to the yaml files
    Manifest_File_Path = Output_Folder / 'index.json'
    Manifest_File_Path.write_text(json.dumps(Manifest_Data, indent=2, sort_keys=True), encoding='utf-8')
    print(f'[Calibration Manifest] Wrote {len(File_Hash_Map)} file hashes to {Manifest_File_Path}')
    # Return the path that was written, in case a caller wants to report or re-stage it
    return Manifest_File_Path


if __name__ == '__main__':
    # This script lives in Distribution/, one level below the calibration YAML files themselves
    Output_Folder = Path(__file__).resolve().parent
    Calibration_Files_Folder = Output_Folder.parent
    Write_The_Manifest_File(Calibration_Files_Folder, Output_Folder)





