from PIL import Image
import re
import os
import sys
from glob import glob
import hashlib
import logging
from collections import defaultdict

# Setup logging to lister.log in the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, "lister.log")
metadata_read_count = 0

# Determine the next session number
def get_next_session_number(log_file):
    session_number = 0
    session_regex = r"^.* - INFO - Starting session (\d+)$"
    try:
        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    match = re.search(session_regex, line.strip())
                    if match:
                        num = int(match.group(1))
                        session_number = max(session_number, num)
        return session_number + 1
    except Exception as e:
        print(f"Error reading session number from {log_file}: {str(e)}", flush=True)
        return 1

# Keep only the last session in lister.log
def keep_last_session(log_file):
    try:
        if not os.path.exists(log_file) or os.path.getsize(log_file) == 0:
            logger.debug(f"No log file or empty file at {log_file}. Creating empty file.")
            open(log_file, "w", encoding="utf-8").close()
            return
        sessions = []
        current_session = []
        session_start = False
        session_regex = r"^.* - INFO - Starting session (\d+)$"
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if re.match(session_regex, line.strip()):
                    if current_session and session_start:
                        sessions.append(current_session)
                    current_session = [line]
                    session_start = True
                else:
                    current_session.append(line)
        if current_session and session_start:
            sessions.append(current_session)
        logger.debug(f"Found {len(sessions)} sessions in {log_file}")
        if sessions:
            last_session = sessions[-1]
            with open(log_file, "w", encoding="utf-8") as f:
                f.writelines(last_session)
            logger.debug(f"Kept last session in {log_file}")
        else:
            logger.debug(f"No valid sessions found in {log_file}. Clearing file.")
            open(log_file, "w", encoding="utf-8").close()
    except Exception as e:
        print(f"Error cleaning {log_file}: {str(e)}", flush=True)
        logger.error(f"Error cleaning {log_file}: {str(e)}")

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Clean log file and set session number
session_number = get_next_session_number(log_file)
keep_last_session(log_file)
logger.info(f"Starting session {session_number}")
logger.info(f"Metadata read count at session start: {metadata_read_count}")

# Regex for extracting actual_id
sky_regex = r"(\d{2,8}\.\w{12,13})"

# Archive and image extensions
archive_extensions = ['.zip', '.rar', '.7z']
image_extensions = ['.jpg', '.jpeg']

def get_model_id(file_path):
    """Extract model_id from image's XPSubject EXIF tag."""
    try:
        with Image.open(file_path) as img:
            exif_data = img.getexif()
            if 0x9c9f in exif_data:
                subject_raw = exif_data[0x9c9f]
                if isinstance(subject_raw, tuple):
                    xp_subject = bytes(subject_raw).decode("utf-16", errors="ignore").rstrip("\x00")
                elif isinstance(subject_raw, bytes):
                    xp_subject = subject_raw.decode("utf-16", errors="ignore").rstrip("\x00")
                else:
                    xp_subject = str(subject_raw)
                actual_id_match = re.search(sky_regex, xp_subject)
                if actual_id_match:
                    model_id = actual_id_match.group(1)
                    logger.debug(f"Extracted model_id: {model_id} from {file_path}")
                    return model_id
            logger.debug(f"No XPSubject found in {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error extracting model_id from {file_path}: {str(e)}")
        return None

def read_xmp_and_exif_data(file_path):
    """Read XMP and EXIF metadata from an image."""
    global metadata_read_count
    metadata_read_count += 1
    logger.info(f"Reading metadata from image: {file_path} (Metadata read #{metadata_read_count})")
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
            if 0x9c9f in exif_data:
                subject_raw = exif_data[0x9c9f]
                if isinstance(subject_raw, tuple):
                    xp_subject = bytes(subject_raw).decode("utf-16", errors="ignore").rstrip("\x00")
                elif isinstance(subject_raw, bytes):
                    xp_subject = subject_raw.decode("utf-16", errors="ignore").rstrip("\x00")
                else:
                    xp_subject = str(subject_raw)

            artist = None
            if 0x13b in exif_data:
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
                    padded_actual_id = f"{actual_id: <21}"
                    is_pro = "ProSky" in artist if artist else False
                    logger.info(f"Successfully extracted metadata for {file_path}: ID={actual_id}, Title={model_title}, Pro={is_pro}")
                    return f"{padded_actual_id} - {model_title} | {subcategory} | {category}", is_pro, actual_id
            logger.warning(f"No valid metadata found for {file_path}")
            return None, None, None
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        print(f"Error processing {file_path}: {str(e)}", flush=True)
        return None, None, None

def verify_existing_report(output_file):
    """Verify the integrity of an existing report file using the hash in [hash_container]."""
    logger.info(f"Verifying report: {output_file}")
    if not os.path.exists(output_file):
        logger.info(f"No report file exists at {output_file}. Starting fresh.")
        return True

    try:
        container_lines = []
        stored_hash = None
        in_container = False
        in_hash_container = False

        with open(output_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                line = line.rstrip("\n")
                if line == "[container]":
                    in_container = True
                    continue
                elif line == "[/container]":
                    in_container = False
                    continue
                elif line == "[hash_container]":
                    in_hash_container = True
                    continue
                elif line == "[/hash_container]":
                    in_hash_container = False
                    continue
                if in_container:
                    container_lines.append(line + "\n")
                elif in_hash_container and line.strip():
                    stored_hash = line.strip()

        if container_lines and stored_hash:
            container_content = "".join(container_lines)
            content_bytes = container_content.encode("utf-8")
            computed_hash = hashlib.sha512(content_bytes).hexdigest()
            if computed_hash != stored_hash:
                logger.error(f"Integrity verification failed. Computed Hash: {computed_hash}, Stored Hash: {stored_hash}")
                print(f"Error: Integrity verification failed for {output_file}.", flush=True)
                return False
            logger.info(f"Integrity verification passed for {output_file}.")
            print(f"Integrity verification passed for {output_file}.", flush=True)
            return True
        else:
            logger.warning(f"Missing [container] or [hash_container] in {output_file}.")
            return True
    except Exception as e:
        logger.error(f"Error verifying {output_file}: {str(e)}")
        print(f"Error verifying {output_file}: {str(e)}.", flush=True)
        return False

def parse_supposed_contents(output_file):
    """Parse the report to generate supposed_contents with model details."""
    logger.info(f"Parsing supposed contents from: {output_file}")
    supposed_contents = []
    model_id_to_entry = {}
    identifiable_model_ids = set()
    unrecognized_models = set()

    if not os.path.exists(output_file):
        logger.info(f"No existing report found at {output_file}")
        return supposed_contents, model_id_to_entry, identifiable_model_ids, unrecognized_models

    current_section = None
    in_container = False
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line in ["[container]", "[/container]", "[hash_container]", "[/hash_container]"]:
                if line == "[container]":
                    in_container = True
                elif line == "[/container]":
                    in_container = False
                continue
            if not in_container:
                continue
            if line.startswith("Identifiable Sky Models:"):
                current_section = "identifiable"
                continue
            elif line.startswith("Unrecognized Sky Models (or missing image):"):
                current_section = "unrecognized"
                continue
            elif line.startswith("Sky-lister results"):
                continue
            if current_section == "identifiable" and line:
                parts = line.split(" - ", 3)
                if len(parts) >= 3:
                    model_id_match = re.search(sky_regex, parts[0])
                    if model_id_match:
                        model_id = model_id_match.group(1)
                        model_type = parts[1].strip()
                        model_desc = parts[2].strip() if len(parts) == 3 else parts[2].strip()
                        desc_parts = [part.strip() for part in model_desc.split("|")]
                        if len(desc_parts) >= 3:
                            model_name = desc_parts[0]
                            subcategory = desc_parts[-2]
                            category = desc_parts[-1]
                            is_pro = model_type.lower() == "pro"
                            line_content = f"{parts[0]} - {model_desc}"
                            entry = {
                                "model_id": model_id,
                                "model_name": model_name,
                                "subcategory": subcategory,
                                "category": category,
                                "is_pro": is_pro,
                                "line": line_content,
                                "archive_ext": None
                            }
                            supposed_contents.append(entry)
                            model_id_to_entry[model_id] = entry
                            identifiable_model_ids.add(model_id)
                            logger.debug(f"Parsed supposed content: {model_id} ({model_name})")
                        else:
                            logger.warning(f"Skipping identifiable model with incomplete metadata: {line}")
                    else:
                        logger.warning(f"Skipping identifiable model with invalid model_id: {line}")
                else:
                    logger.warning(f"Skipping malformed identifiable model entry: {line}")
            elif current_section == "unrecognized" and line:
                unrecognized_models.add(line)
                logger.debug(f"Parsed unrecognized model: {line}")

    logger.info(f"Parsed {len(supposed_contents)} supposed contents, {len(unrecognized_models)} unrecognized models")
    return supposed_contents, model_id_to_entry, identifiable_model_ids, unrecognized_models

def get_subfolders(source_folder):
    """Get all subfolders in the source folder, including nested ones."""
    logger.info(f"Scanning for subfolders in: {source_folder}")
    subfolders = []
    for root, dirs, _ in os.walk(source_folder):
        for dir_name in dirs:
            subfolder_path = os.path.join(root, dir_name)
            subfolders.append(subfolder_path)
    logger.info(f"Found {len(subfolders)} subfolders")
    return subfolders

def scan_subfolder(subfolder_path, identifiable_model_ids, model_id_to_entry):
    """Scan a subfolder for actual contents, identifying model names."""
    logger.info(f"Scanning subfolder: {subfolder_path}")
    print(f"Scanning subfolder: {subfolder_path}", flush=True)
    
    actual_contents = defaultdict(list)
    files = os.listdir(subfolder_path)
    logger.debug(f"Found {len(files)} files in {subfolder_path}")
    
    for file in files:
        file_path = os.path.join(subfolder_path, file)
        if os.path.isfile(file_path):
            base_name, ext = os.path.splitext(file)
            ext = ext.lower()
            if ext in archive_extensions or ext in image_extensions:
                model_id_match = re.search(sky_regex, base_name)
                if model_id_match:
                    model_id = model_id_match.group(1)
                    actual_contents[model_id].append((file, ext))
                    logger.debug(f"Found file for model_id {model_id}: {file} ({ext})")
    
    new_identifiable_models = []
    new_unrecognized_models = set()
    
    for model_id, files in actual_contents.items():
        archive_file = None
        image_file = None
        for file_name, ext in files:
            if ext in archive_extensions:
                archive_file = file_name
            elif ext in image_extensions:
                image_file = file_name
        
        if archive_file and image_file:
            if model_id in identifiable_model_ids:
                logger.info(f"Model {model_id} already in identifiable models, updating archive extension")
                if model_id in model_id_to_entry:
                    model_id_to_entry[model_id]["archive_ext"] = os.path.splitext(archive_file)[1]
                continue
            image_path = os.path.join(subfolder_path, image_file)
            logger.info(f"Reading metadata for new model {model_id} from {image_path}")
            result, is_pro, extracted_model_id = read_xmp_and_exif_data(image_path)
            if result and extracted_model_id and extracted_model_id == model_id:
                identifiable_model_ids.add(model_id)
                desc_parts = [part.strip() for part in result.split("|")]
                if len(desc_parts) >= 3:
                    model_name = desc_parts[0]
                    subcategory = desc_parts[-2]
                    category = desc_parts[-1]
                    entry = {
                        "model_id": model_id,
                        "model_name": model_name,
                        "subcategory": subcategory,
                        "category": category,
                        "is_pro": is_pro,
                        "line": result,
                        "archive_ext": os.path.splitext(archive_file)[1]
                    }
                    new_identifiable_models.append(entry)
                    model_id_to_entry[model_id] = entry
                    logger.info(f"Added new identifiable model: {model_id} ({model_name})")
                    print(f"Added new identifiable model: {model_id} from {archive_file}", flush=True)
            else:
                new_unrecognized_models.add(archive_file)
                logger.info(f"Marked as unrecognized: {archive_file}")
        elif archive_file:
            new_unrecognized_models.add(archive_file + " (no accompanying image)")
            logger.info(f"Marked as unrecognized (no image): {archive_file}")
    
    return new_identifiable_models, new_unrecognized_models

def write_report(output_file, identifiable_models, unrecognized_models, folder_name):
    """Write the report file with entries in [container] and hash in [hash_container]."""
    logger.info(f"Writing report to {output_file}")
    identifiable_models.sort(key=numeric_sort_key)
    pro_count = sum(1 for model in identifiable_models if model["is_pro"])
    free_count = len(identifiable_models) - pro_count
    total_identifiable = len(identifiable_models)
    total_unrecognized = len(unrecognized_models)

    lines = []
    header = (
        f"Sky-lister results: {total_identifiable} Identifiable "
        f"({pro_count} Pro and {free_count} FREE), "
        f"{total_unrecognized} Unrecognized/Non-Sky models in {folder_name}\n\n"
    )
    lines.append(header)
    lines.append("Identifiable Sky Models:\n")
    for model in identifiable_models:
        model_type = "Pro" if model["is_pro"] else "FREE"
        model_id = model["line"].split(" - ")[0].strip()
        model_desc = model["line"].split(" - ")[1].strip()
        lines.append(f"{model_id} - {model_type: <4} - {model_desc}\n")
    lines.append("\nUnrecognized Sky Models (or missing image):\n")
    for model in sorted(unrecognized_models):
        lines.append(model + "\n")

    container_content = "".join(lines)
    content_bytes = container_content.encode("utf-8")
    integrity_hash = hashlib.sha512(content_bytes).hexdigest()
    logger.info(f"Computed SHA-512 hash for container content: {integrity_hash}")

    with open(output_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("[container]\n")
        f.write(container_content)
        f.write("[/container]\n\n")
        f.write("[hash_container]\n")
        f.write(integrity_hash + "\n")
        f.write("[/hash_container]\n")
    logger.info(f"Report written to {output_file}")

def numeric_sort_key(entry):
    """Sort key for model lines based on numeric and hex parts of model_id."""
    if isinstance(entry, dict):
        line = entry["line"]
    else:
        line = entry  # Handle old string format for backward compatibility
    actual_id = line.split(" - ")[0].strip()
    numeric_part, hex_part = actual_id.split(".", 1)
    return (int(numeric_part), hex_part)

def generate_report(source_folder):
    """Generate a report by comparing supposed and actual folder contents."""
    logger.info(f"Starting report generation for source folder: {source_folder}")
    if not os.path.isdir(source_folder):
        logger.error(f"Invalid directory: {source_folder}")
        print(f"Error: {source_folder} is not a valid directory.", flush=True)
        return

    folder_name = os.path.basename(source_folder)
    parent_folder = os.path.dirname(source_folder)
    output_file = os.path.join(parent_folder, f"{folder_name}.txt")

    if not verify_existing_report(output_file):
        logger.error(f"Aborting due to integrity verification failure for {output_file}")
        print(f"Aborting report generation due to integrity verification failure.", flush=True)
        sys.exit(1)

    supposed_contents, model_id_to_entry, identifiable_model_ids, unrecognized_models = parse_supposed_contents(output_file)

    subfolders = get_subfolders(source_folder)

    all_identifiable_models = supposed_contents.copy()
    all_unrecognized_models = set(unrecognized_models)
    removed_models = []

    for subfolder in subfolders:
        new_identifiable, new_unrecognized = scan_subfolder(subfolder, identifiable_model_ids, model_id_to_entry)
        all_identifiable_models.extend(new_identifiable)
        all_unrecognized_models.update(new_unrecognized)

    subfolder_models = set()
    for subfolder in subfolders:
        files = os.listdir(subfolder)
        for file in files:
            base_name = os.path.splitext(file)[0]
            model_id_match = re.search(sky_regex, base_name)
            if model_id_match:
                subfolder_models.add(model_id_match.group(1))

    filtered_identifiable_models = []
    for model in all_identifiable_models:
        if model["model_id"] in subfolder_models:
            filtered_identifiable_models.append(model)
        else:
            removed_models.append(model["model_id"])
            logger.info(f"Removed model {model['model_id']} (not found in subfolders)")
            print(f"Removed model {model['model_id']} (not found in subfolders)", flush=True)

    write_report(output_file, filtered_identifiable_models, all_unrecognized_models, folder_name)
    logger.info(f"Report generation complete: {output_file}")
    print(f"Report generation complete: {output_file}", flush=True)
    if removed_models:
        logger.info(f"Removed {len(removed_models)} models: {removed_models}")
        print(f"Removed {len(removed_models)} models: {removed_models}", flush=True)

if __name__ == "__main__":
    logger.info("Script started")
    print("Starting report generation...", flush=True)
    if len(sys.argv) > 1:
        source_folder = " ".join(sys.argv[1:]).strip()
        generate_report(source_folder)
    else:
        source_folder = input("Enter the source folder path: ").strip()
        generate_report(source_folder)
    logger.info(f"Metadata read count at session end: {metadata_read_count}")
    logger.info("Script finished")
    print(f"Metadata read count for session {session_number}: {metadata_read_count}", flush=True)
