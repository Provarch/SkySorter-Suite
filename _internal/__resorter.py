import os
import sys
import json
import re
from glob import glob
from shutil import move, rmtree
from PIL import Image
from pathlib import Path

# Regex for extracting actual_id
sky_regex = r"(\d{2,8}\.\w{12,13})"

# Archive file extensions
archive_extensions = {'.zip', '.rar', '.7z'}

def read_config(config_path, default_config_path):
    """Read or create sssuite.cfg, using defaults from default_config.json."""
    # Load default config from default_config.json
    try:
        with open(default_config_path, 'r', encoding='utf-8') as f:
            default_config = json.load(f)
    except FileNotFoundError:
        print(f"Default config not found at {default_config_path}, using empty defaults", flush=True)
        default_config = {}
    except Exception as e:
        print(f"Error loading default config {default_config_path}: {str(e)}", flush=True)
        default_config = {}
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        else:
            # Create sssuite.cfg with defaults
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created new {config_path} with default config", flush=True)
            return default_config
    except Exception as e:
        print(f"Error handling config {config_path}: {str(e)}", flush=True)
        return default_config

def read_xmp_and_exif_data(file_path):
    """Read XMP and EXIF data to extract model info."""
    try:
        with Image.open(file_path) as img:
            img.load()
            xmp_data = img.getxmp()
            title = None
            if "xmpmeta" in xmp_data and "RDF" in xmp_data["xmpmeta"]:
                rdf = xmp_data["xmpmeta"]["RDF"]
                if "Description" in rdf:
                    desc = rdf["Description"]
                    if isinstance(desc, dict) and "title" in desc:
                        title_data = desc["title"]
                        if isinstance(title_data, dict) and "Alt" in title_data:
                            title = title_data["Alt"].get("li", {}).get("text")

            xp_subject = None
            exif_data = img.getexif()
            if 0x9c9f in exif_data:  # XPSubject tag
                subject_raw = exif_data[0x9c9f]
                if isinstance(subject_raw, tuple):
                    xp_subject = bytes(subject_raw).decode("utf-16", errors="ignore").rstrip("\x00")
                elif isinstance(subject_raw, bytes):
                    xp_subject = subject_raw.decode("utf-16", errors="ignore").rstrip("\x00")

            artist = None
            if 0x13b in exif_data:  # Artist tag
                artist_raw = exif_data[0x13b]
                if isinstance(artist_raw, bytes):
                    artist = artist_raw.decode("utf-8", errors="ignore")
                elif isinstance(artist_raw, str):
                    artist = artist_raw

            if title and xp_subject:
                actual_id_match = re.search(sky_regex, xp_subject)
                actual_id = actual_id_match.group(1) if actual_id_match else None
                title_parts = [part.strip() for part in title.split("|")]
                if len(title_parts) >= 3:
                    model_title = title_parts[0]
                    subcategory = title_parts[-2]
                    category = title_parts[-1]
                    is_pro = "ProSky" in artist if artist else False
                    return actual_id, model_title, subcategory, category, is_pro
            return None, None, None, None, None
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}", flush=True)
        return None, None, None, None, None

def get_model_archives_and_images(source_folder):
    """Find model archives and their corresponding preview image using sky_regex, ignoring folders with __ prefix."""
    archive_image_pairs = {}
    
    print(f"Scanning folder: {source_folder}", flush=True)
    # Find all archive files, skipping folders with __ prefix
    for root, dirs, files in os.walk(source_folder):
        # Check if any part of the path contains a folder starting with __
        path_parts = os.path.normpath(root).split(os.sep)
        if any(part.startswith('__') for part in path_parts):
            print(f"Skipping folder with __ prefix: {root}", flush=True)
            continue
        for file in files:
            if file.lower().endswith(tuple(archive_extensions)):
                archive_path = os.path.join(root, file)
                # Check if the file matches sky_regex
                filename = os.path.basename(archive_path)
                actual_id_match = re.search(sky_regex, filename)
                if actual_id_match:
                    actual_id = actual_id_match.group(1)
                    # Get base name up to the last dot
                    base_name = filename.rsplit('.', 1)[0]
                    # Check for .jpeg first, then .jpg
                    jpeg_path = os.path.join(root, f"{base_name}.jpeg")
                    jpg_path = os.path.join(root, f"{base_name}.jpg")
                    preview_path = None
                    if os.path.exists(jpeg_path):
                        preview_path = jpeg_path
                    elif os.path.exists(jpg_path):
                        preview_path = jpg_path
                    archive_image_pairs[archive_path] = preview_path
                    if not preview_path:
                        print(f"No preview found for {filename}", flush=True)
    
    return archive_image_pairs

def capitalize_subcategory(subcategory):
    """Capitalize every word in the subcategory."""
    if not subcategory:
        return "Uncategorized"
    return ' '.join(word.capitalize() for word in subcategory.split())

def determine_target_folder(actual_id, category, subcategory, sorting_type, base_folder):
    """Determine the target folder based on sorting type."""
    if sorting_type == "ID" and actual_id:
        try:
            namenumber = int(actual_id.split('.')[0])
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
            return os.path.join(base_folder, sorted_sub)
        except ValueError:
            return os.path.join(base_folder, "Uncategorized")
    elif sorting_type == "CAT" and category and subcategory:
        # CATEGORY is all uppercase, Subcategory has every word capitalized
        category_upper = category.upper()
        subcategory_cap = capitalize_subcategory(subcategory)
        return os.path.join(base_folder, category_upper, subcategory_cap)
    return os.path.join(base_folder, "Uncategorized")

def is_already_sorted(archive_path, actual_id, category, subcategory, sorting_type, base_folder):
    """Check if the model is already sorted according to the current sorting type."""
    current_folder = os.path.dirname(archive_path)
    current_parent = os.path.dirname(current_folder)
    expected_folder = determine_target_folder(actual_id, category, subcategory, sorting_type, base_folder)
    
    if sorting_type == "ID":
        return os.path.normpath(current_folder) == os.path.normpath(expected_folder)
    elif sorting_type == "CAT":
        # For CAT, check if the current folder matches CATEGORY\Subcategory or parent matches CATEGORY
        category_upper = category.upper() if category else "Uncategorized"
        subcategory_cap = capitalize_subcategory(subcategory)
        expected_parent = os.path.join(base_folder, category_upper)
        return (os.path.normpath(current_folder) == os.path.normpath(expected_folder) or
                os.path.normpath(current_parent) == os.path.normpath(expected_parent))
    return False

def move_files(archive_path, image_path, target_folder, duplicates_folder, actual_id):
    """Move model archive and its preview (if available) to the target folder or duplicates folder if model_id exists."""
    # Check for existing model_id in target folder
    model_id_pattern = os.path.join(target_folder, f"{actual_id}.*")
    existing_files = glob(model_id_pattern)
    existing_archive = any(f.lower().endswith(tuple(archive_extensions)) for f in existing_files)
    
    # If an archive with the same model_id exists, move to duplicates folder
    if existing_archive:
        print(f"Duplicate model_id {actual_id} found in {target_folder}, moving to {duplicates_folder}", flush=True)
        os.makedirs(duplicates_folder, exist_ok=True)
        target_folder = duplicates_folder
    
    os.makedirs(target_folder, exist_ok=True)
    
    # Move archive first
    archive_name = os.path.basename(archive_path)
    new_archive_path = os.path.join(target_folder, archive_name)
    move(archive_path, new_archive_path)
    print(f"Moved archive to: {new_archive_path}", flush=True)
    
    # Move preview if exists
    if image_path:
        image_name = os.path.basename(image_path)
        new_image_path = os.path.join(target_folder, image_name)
        move(image_path, new_image_path)
        print(f"Moved preview to: {new_image_path}", flush=True)
    else:
        print(f"No preview available for {archive_name}", flush=True)

def clean_empty_dirs(source_folder, base_folder):
    """Move empty directories from source folder to __empty subfolder in base folder, checking parent folders."""
    empty_folder = os.path.join(base_folder, "__empty")
    os.makedirs(empty_folder, exist_ok=True)
    
    moved_dirs = []
    moved_dirs_set = set()  # Track moved directories to prevent reprocessing
    folders_to_check = [source_folder]
    
    for folder in folders_to_check:
        print(f"Checking for empty directories in: {folder}", flush=True)
        # Walk through directories in reverse to handle nested dirs
        for root, dirs, files in os.walk(folder, topdown=False):
            # Skip if already moved in this run
            if os.path.normpath(root) in moved_dirs_set:
                print(f"Skipping already moved directory: {root}", flush=True)
                continue
            # Check if directory is empty (no files and no subdirs)
            if not files and not dirs:
                try:
                    # Move the empty directory
                    dir_name = os.path.basename(root)
                    dest_dir = os.path.join(empty_folder, dir_name)
                    counter = 1
                    while os.path.exists(dest_dir):
                        dest_dir = os.path.join(empty_folder, f"{dir_name}_{counter}")
                        counter += 1
                    os.rename(root, dest_dir)
                    moved_dirs.append(f"Moved empty dir: {root} to {dest_dir}")
                    moved_dirs_set.add(os.path.normpath(dest_dir))
                    
                    # Check parent directories for emptiness
                    parent = os.path.dirname(root)
                    while parent != os.path.normpath(folder):
                        if os.path.normpath(parent) in moved_dirs_set:
                            print(f"Skipping already moved parent: {parent}", flush=True)
                            break
                        parent_dirs = []
                        parent_files = []
                        for p_root, p_dirs, p_files in os.walk(parent):
                            if p_root == parent:
                                parent_dirs = p_dirs
                                parent_files = p_files
                                break
                        if not parent_files and not parent_dirs:
                            parent_name = os.path.basename(parent)
                            parent_dest = os.path.join(empty_folder, parent_name)
                            counter = 1
                            while os.path.exists(parent_dest):
                                parent_dest = os.path.join(empty_folder, f"{parent_name}_{counter}")
                                counter += 1
                            os.rename(parent, parent_dest)
                            moved_dirs.append(f"Moved empty parent dir: {parent} to {parent_dest}")
                            moved_dirs_set.add(os.path.normpath(parent_dest))
                            parent = os.path.dirname(parent)
                        else:
                            break
                except Exception as e:
                    print(f"Error moving empty dir {root}: {str(e)}", flush=True)
    
    return moved_dirs

def delete_empty_if_no_files(source_folder, base_folder):
    """Check if __empty and __duplicates folders and their subfolders have no files, and delete if completely empty."""
    folders_to_check = [
        os.path.join(base_folder, "__empty"),
        os.path.join(source_folder, "__duplicates")
    ]
    
    for folder in folders_to_check:
        if not os.path.exists(folder):
            print(f"No {os.path.basename(folder)} folder found in {os.path.dirname(folder)}", flush=True)
            continue
        
        # Check for any files in the folder and its subfolders
        has_files = False
        for root, _, files in os.walk(folder):
            if files:
                has_files = True
                break
        
        if has_files:
            print(f"{os.path.basename(folder)} folder contains files, not deleting: {folder}", flush=True)
        else:
            try:
                rmtree(folder)
                print(f"Deleted empty {os.path.basename(folder)} folder: {folder}", flush=True)
            except Exception as e:
                print(f"Error deleting {os.path.basename(folder)} folder {folder}: {str(e)}", flush=True)

def main(source_folder, dest_folder=None):
    """Main function to re-sort model archives and previews within the source or destination folder."""
    # Read config
    script_dir = Path(__file__).parent
    config_path = script_dir / "sssuite.cfg"
    default_config_path = script_dir / "default_config.json"
    config = read_config(config_path, default_config_path)
    sorting_type = config.get("sorting_type", "CAT")
    print(f"Using sorting type: {sorting_type}", flush=True)
    
    # Validate source_folder
    if not source_folder or not os.path.exists(source_folder):
        print(f"Error: Source folder '{source_folder}' does not exist", flush=True)
        sys.exit(1)
    print(f"Using source folder: {source_folder}", flush=True)
    
    # Set base folder for sorting (dest_folder if provided, else source_folder)
    base_folder = dest_folder if dest_folder else source_folder
    print(f"Using base folder: {base_folder}", flush=True)
    
    # Define duplicates folder path in source_folder (create only when needed)
    duplicates_folder = os.path.join(source_folder, "__duplicates")
    
    # Get archive and image pairs
    archive_image_pairs = get_model_archives_and_images(source_folder)
    
    for archive_path, image_path in archive_image_pairs.items():
        print(f"\nProcessing archive: {archive_path}", flush=True)
        
        # Initialize variables
        actual_id, model_title, subcategory, category, is_pro = (None, None, None, None, None)
        
        # Extract actual_id from filename
        filename = os.path.basename(archive_path)
        actual_id_match = re.search(sky_regex, filename)
        if not actual_id_match:
            print(f"Skipping archive, does not match sky_regex: {filename}", flush=True)
            continue
        actual_id = actual_id_match.group(1)
        print(f"Model ID: {actual_id}", flush=True)
        
        # Read metadata from preview to check for category and subcategory
        if image_path:
            actual_id, model_title, subcategory, category, is_pro = read_xmp_and_exif_data(image_path)
            if category and subcategory:
                print(f"Category: {category}, Subcategory: {subcategory}, Pro: {is_pro}", flush=True)
            else:
                print(f"Skipping archive, no valid category/subcategory in preview: {image_path}", flush=True)
                continue
        else:
            print(f"Skipping archive, no preview found for: {filename}", flush=True)
            continue
        
        # Determine target folder
        target_folder = determine_target_folder(actual_id, category, subcategory, sorting_type, base_folder)
        
        # Check if already sorted
        if is_already_sorted(archive_path, actual_id, category, subcategory, sorting_type, base_folder):
            print(f"Status: Already sorted by {sorting_type} in {os.path.dirname(archive_path)}", flush=True)
        else:
            print(f"Status: Not sorted by {sorting_type}", flush=True)
            print(f"Next location: {target_folder}", flush=True)
            move_files(archive_path, image_path, target_folder, duplicates_folder, actual_id)
    
    # Clean up empty directories after sorting
    print(f"\nCleaning up empty directories in source folder", flush=True)
    moved_dirs = clean_empty_dirs(source_folder, base_folder)
    for msg in moved_dirs:
        print(msg, flush=True)
    if not moved_dirs:
        print("No empty directories found in source folder.", flush=True)
    
    # Delete __empty and __duplicates folders if they contain no files
    print(f"\nChecking __empty and __duplicates folders for deletion", flush=True)
    delete_empty_if_no_files(source_folder, base_folder)

if __name__ == "__main__":
    print("Starting re-sorter...", flush=True)
    if len(sys.argv) == 2:
        # One argument: source_folder only
        main(source_folder=sys.argv[1].strip())
    elif len(sys.argv) == 3:
        # Two arguments: source_folder and dest_folder
        main(source_folder=sys.argv[1].strip(), dest_folder=sys.argv[2].strip())
    else:
        print("Usage: __re-sorter.py <source_folder> [dest_folder]", flush=True)
        sys.exit(1)
