import requests
import re
import subprocess
import os
import shutil
from pathlib import Path
from typing import List, Optional
from PIL import Image, UnidentifiedImageError

# Sky regex for matching model IDs
sky_regex = re.compile(r'\b(\d{3,8}\.\w{12,13})')

# Supported archive and image extensions
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z'}

def determine_sorted_folder(sorted_path: str, filename: str) -> str:
    """Determines the save folder based on the numerical part of the filename."""
    try:
        namenumber = int(filename.split('.')[0])
        if 1 <= namenumber < 20000:
            sorted_sub = "!_0010k"
        elif 20000 <= namenumber < 50000:
            sorted_sub = "!_0020k"
        elif 50000 <= namenumber < 100000:
            sorted_sub = "!_0050k"
        elif 100000 <= namenumber < 200000:
            sorted_sub = "!_0100k"
        elif 200000 <= namenumber < 500000:
            sorted_sub = "!_0200k"
        elif 500000 <= namenumber < 1000000:
            sorted_sub = "!_0500k"
        elif 1000000 <= namenumber < 2000000:
            sorted_sub = "!_1000k"
        elif 2000000 <= namenumber < 3000000:
            sorted_sub = "!_2000k"
        elif 3000000 <= namenumber < 4000000:
            sorted_sub = "!_3000k"
        elif 4000000 <= namenumber < 5000000:
            sorted_sub = "!_4000k"
        elif 5000000 <= namenumber < 6000000:
            sorted_sub = "!_5000k"
        elif 6000000 <= namenumber < 7000000:
            sorted_sub = "!_6000k"
        elif 7000000 <= namenumber < 8000000:
            sorted_sub = "!_7000k"
        elif 8000000 <= namenumber < 9000000:
            sorted_sub = "!_8000k"
        elif 9000000 <= namenumber < 10000000:
            sorted_sub = "!_9000k"
        else:
            sorted_sub = "!_10000k"
        return os.path.join(sorted_path, sorted_sub)
    except ValueError:
        return os.path.join(sorted_path, "Uncategorized")

def process_cmd(exif_cmd: str, source_folder: Path, model_archive: Path, model_previews: List[Path], destination_folder: Path = None, sort_by_id: bool = False) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Process the exif_cmd: extract valid_id, check for existing preview in destination,
    download preview if not exists, ensure valid JPEG, execute EXIF command with retry,
    sort into destination_folder based on category or ID, move duplicates to __duplicates,
    and clean up old previews. Returns (valid_id, valid_prv_path, full_cmd, exif_result).
    """
    valid_id = None
    match = sky_regex.search(exif_cmd)
    if match:
        valid_id = match.group(0)
    
    if not valid_id:
        print("⚠️ No valid_id found in exif_cmd.")
        return None, None, None, None

    # Determine base folder for sorting (destination_folder if provided, else source_folder)
    base_folder = destination_folder if destination_folder else source_folder

    # Determine destination folder for checking duplicates
    if sort_by_id:
        dest_folder = Path(determine_sorted_folder(str(base_folder), valid_id))
    else:
        title_match = re.search(r'-XMP:Title="([^"]+)"', exif_cmd)
        if title_match:
            title_parts = title_match.group(1).split(" | ")
            if len(title_parts) >= 3:
                category = title_parts[-1].upper()
                subcategory = title_parts[-2]
                dest_folder = base_folder / category / subcategory
            else:
                dest_folder = base_folder
        else:
            dest_folder = base_folder

    # Check if archive already exists in the destination folder
    for ext in ARCHIVE_EXTENSIONS:
        potential_prv_path = dest_folder / f"{valid_id}{ext}"
        if potential_prv_path.exists():
            duplicates_folder = source_folder / "__duplicates"
            duplicates_folder.mkdir(exist_ok=True)

            # Move model_archive to __duplicates
            if model_archive and model_archive.exists():
                new_archive_path = duplicates_folder / model_archive.name
                try:
                    shutil.move(model_archive, new_archive_path)
                except OSError as e:
                    print(f"⚠️ Error moving model_archive to __duplicates: {e}")

            # Move model_previews to __duplicates
            for preview in model_previews:
                if preview.exists():
                    new_preview_path = duplicates_folder / preview.name
                    try:
                        shutil.move(preview, new_preview_path)
                    except OSError as e:
                        print(f"⚠️ Error moving preview to __duplicates: {e}")

            return valid_id, None, None, None

    subject_match = re.search(r'-XPSubject="([^"]+)"', exif_cmd)
    preview_url = subject_match.group(1) if subject_match else None
    if not preview_url:
        print("⚠️ No -XPSubject URL found in exif_cmd.")
        return valid_id, None, None, None
    valid_prv_path = source_folder / f"{valid_id}.jpeg"
    try:
        # Check if source folder is writable
        if not os.access(source_folder, os.W_OK):
            print(f"❌ Error: Source folder {source_folder} is not writable.")
            return valid_id, None, None, None
        # If file exists, ensure it’s writable
        if valid_prv_path.exists():
            try:
                os.chmod(valid_prv_path, 0o666)
            except OSError as e:
                print(f"⚠️ Cannot modify permissions for {valid_prv_path}: {e}")
                return valid_id, None, None, None
        response = requests.get(preview_url, timeout=5)
        response.raise_for_status()
        # First attempt to write
        try:
            with open(valid_prv_path, 'wb') as f:
                f.write(response.content)
            print(f"📥 Downloaded preview: {valid_prv_path}")
        except PermissionError as e:
            print(f"❌ PermissionError on {valid_prv_path}: {e}. Attempting to unlock and retry...")
            # Try unlocking and retrying once
            try:
                os.chmod(valid_prv_path, 0o666)
                with open(valid_prv_path, 'wb') as f:
                    f.write(response.content)
                print(f"📥 Downloaded preview after retry: {valid_prv_path}")
            except (PermissionError, OSError) as retry_e:
                print(f"❌ Retry failed for {valid_prv_path}: {retry_e}. Skipping file.")
                return valid_id, None, None, None
    except requests.RequestException as e:
        print(f"⚠️ Error downloading preview from {preview_url}: {e}")
        return valid_id, None, None, None

    # Verify and resave as clean JPEG
    try:
        with Image.open(valid_prv_path) as img:
            img = img.convert('RGB')
            img.save(valid_prv_path, 'JPEG', quality=95)
        print(f"✅ Resaved {valid_prv_path} as a clean JPEG.")
    except UnidentifiedImageError:
        print(f"❌ Downloaded file is not a valid image: {valid_prv_path}")
        os.remove(valid_prv_path)
        return valid_id, None, None, None
    except Exception as e:
        print(f"⚠️ Error verifying or resaving image: {e}")
        os.remove(valid_prv_path)
        return valid_id, None, None, None

    # Define exiftool path
    script_dir = Path(__file__).parent
    exiftool = script_dir / "exiftool.exe"
    if not exiftool.exists():
        print(f"⚠️ exiftool.exe not found at {exiftool}")
        return valid_id, valid_prv_path, None, None

    full_cmd = f'"{exiftool}" {exif_cmd} -Software=\"SkySorter Pro v.95\" -Copyright=\"Acquired\" -overwrite_original "{valid_prv_path}"'
    #print(f"📋 Generated EXIF command: {full_cmd}")

    for attempt in range(2):
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            exif_result = result.stdout.strip()
            if result.returncode == 0 and "1 image files updated" in exif_result:
                print("✅ EXIF command executed successfully: 1 image files updated")
                break
            else:
                print(f"⚠️ EXIF command failed with output: {exif_result}")
                print(f"Error details: {result.stderr}")
                if attempt == 0:
                    print("⚠️ Possible corrupt JPEG, resaving and retrying...")
                    with Image.open(valid_prv_path) as img:
                        img = img.convert('RGB')
                        img.save(valid_prv_path, 'JPEG', quality=95)
                    print(f"✅ Resaved {valid_prv_path} for retry.")
                else:
                    return valid_id, valid_prv_path, full_cmd, exif_result
        except Exception as e:
            print(f"❌ Error executing EXIF command: {e}")
            return valid_id, valid_prv_path, full_cmd, None

    # Sorting logic
    dest_folder.mkdir(parents=True, exist_ok=True)
    print(f"📌 Sorting to: {dest_folder}")

    # Rename and move model_archive
    if model_archive and model_archive.exists():
        original_ext = '.' + model_archive.name.rsplit('.', 1)[-1]
        new_name = f"{valid_id}{original_ext}"
        new_archive_path = dest_folder / new_name
        try:
            shutil.move(model_archive, new_archive_path)
            print(f"📌 Moved and renamed model_archive to: {new_archive_path}")
            model_archive = new_archive_path
        except OSError as e:
            print(f"⚠️ Error moving/renaming model_archive: {e}")

    # Move the preview image
    if valid_prv_path.exists():
        new_prv_path = dest_folder / valid_prv_path.name
        try:
            shutil.move(valid_prv_path, new_prv_path)
            print(f"📌 Moved preview image to: {new_prv_path}")
            valid_prv_path = new_prv_path
        except OSError as e:
            print(f"⚠️ Error moving preview image: {e}")

    # Remove all old preview images
    for preview in model_previews:
        if preview.exists() and preview != valid_prv_path:
            try:
                os.remove(preview)
                print(f"🗑️ Removed old preview: {preview}")
            except OSError as e:
                print(f"⚠️ Error removing old preview {preview}: {e}")

    return valid_id, valid_prv_path, full_cmd, exif_result
