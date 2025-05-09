import zipfile
import rarfile
import py7zr
import os
from pathlib import Path
from typing import Optional, List, Tuple

def get_archive_contents(archive_file_path: str) -> Tuple[Optional[List[str]], str]:
    """Extract the list of files from an archive (zip, rar, 7z), correcting extension if needed.
    Returns a tuple of (contents, corrected_file_path). Skips filenames with incompatible characters."""
    archive_file_path = str(archive_file_path)
    path_obj = Path(archive_file_path)
    
    # Function to detect true archive format
    def get_true_archive_format(file_path: str) -> str:
        try:
            if zipfile.is_zipfile(file_path):
                return "ZIP"
            elif rarfile.is_rarfile(file_path):
                return "RAR"
            elif py7zr.is_7zfile(file_path):
                return "7Z"
            else:
                return "Unknown"
        except Exception:
            return "Unknown"
    
    # Function to rename archive to correct extension
    def rename_archive_to_genuine(file_path: str, true_format: str) -> str:
        file_extension = path_obj.suffix.lower()
        genuine_extension = {"ZIP": ".zip", "RAR": ".rar", "7Z": ".7z"}.get(true_format)
        if file_extension != genuine_extension:
            new_file_path = str(path_obj.with_suffix(genuine_extension))
            try:
                os.rename(file_path, new_file_path)
                print(f"Corrected format: {file_path} -> {new_file_path}")
                return new_file_path
            except Exception as e:
                print(f"Failed to rename {file_path}: {e}")
                return file_path
        return file_path

    # Get true format and rename if necessary
    true_format = get_true_archive_format(archive_file_path)
    if true_format == "Unknown":
        print(f"⚠️ Error: Invalid or unreadable archive: {archive_file_path}")
        return None, archive_file_path
    
    # Correct the file extension if needed
    corrected_path = rename_archive_to_genuine(archive_file_path, true_format)
    
    # Process the archive based on its true format
    valid_contents = []
    
    if true_format == "RAR":
        try:
            with rarfile.RarFile(corrected_path) as rf:
                for filename in rf.namelist():
                    try:
                        # Ensure filename is decodable and valid
                        filename.encode('utf-8').decode('utf-8')
                        valid_contents.append(filename)
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        print(f"⚠️ Skipped invalid filename in RAR archive: {filename}")
        except (rarfile.NotRarFile, rarfile.RarCannotExec, rarfile.NeedFirstVolume):
            print(f"⚠️ Error: Invalid RAR file after correction: {corrected_path}")
            return None, corrected_path
    
    elif true_format == "ZIP":
        try:
            with zipfile.ZipFile(corrected_path) as zf:
                # Get raw file info to handle encoding manually
                for file_info in zf.infolist():
                    try:
                        # Try UTF-8 decoding first
                        filename = file_info.filename
                        filename.encode('utf-8').decode('utf-8')
                        valid_contents.append(filename)
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        try:
                            # Fallback to CP437 for non-UTF-8 ZIP filenames
                            filename = file_info.filename.encode('latin1').decode('cp437')
                            filename.encode('utf-8').decode('utf-8')  # Ensure it's UTF-8 compatible
                            valid_contents.append(filename)
                        except (UnicodeEncodeError, UnicodeDecodeError):
                            print(f"⚠️ Skipped invalid filename in ZIP archive: {file_info.filename}")
        except zipfile.BadZipFile:
            print(f"⚠️ Error: Invalid ZIP file after correction: {corrected_path}")
            return None, corrected_path
        except Exception as e:
            print(f"⚠️ Error reading ZIP archive {corrected_path}: {e}")
            return None, corrected_path
    
    elif true_format == "7Z":
        try:
            with py7zr.SevenZipFile(corrected_path) as zf:
                for filename in zf.getnames():
                    try:
                        # Ensure filename is decodable and valid
                        filename.encode('utf-8').decode('utf-8')
                        valid_contents.append(filename)
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        print(f"⚠️ Skipped invalid filename in 7Z archive: {filename}")
        except py7zr.Bad7zFile:
            print(f"⚠️ Error: Invalid 7Z file after correction: {corrected_path}")
            return None, corrected_path
    
    if not valid_contents:
        print(f"⚠️ No valid filenames found in archive: {corrected_path}")
        return None, corrected_path
    
    return valid_contents, corrected_path
