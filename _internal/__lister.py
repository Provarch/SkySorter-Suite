from PIL import Image
import re
import os
import sys
from glob import glob
import hashlib
import logging

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

# Archive file extensions
archive_extensions = ['.zip', '.rar', '.7z']  # Ordered preference

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

def numeric_sort_key(line):
    actual_id = line.split(" - ")[0].strip()
    numeric_part, hex_part = actual_id.split(".", 1)
    return (int(numeric_part), hex_part)

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
            logger.debug(f"Container content length: {len(container_content)}, first 100 chars: {container_content[:100].replace('\n', '\\n')}")
            if computed_hash != stored_hash:
                logger.error(f"Integrity verification failed. Computed Hash: {computed_hash}, Stored Hash: {stored_hash}")
                print(f"Error: Integrity verification failed for {output_file}. The file may have been tampered with.", flush=True)
                print(f"Computed Hash: {computed_hash}", flush=True)
                print(f"Stored Hash: {stored_hash}", flush=True)
                print(f"Please remove {output_file} and run the script again to generate a new report.", flush=True)
                return False
            logger.info(f"Integrity verification passed for {output_file}.")
            print(f"Integrity verification passed for {output_file}.", flush=True)
            return True
        else:
            logger.warning(f"Missing [container] or [hash_container] in {output_file}. Lines processed: {len(lines)}")
            logger.debug(f"First few lines: {''.join(lines[:5])[:100].replace('\n', '\\n')}")
            hash_file = output_file.replace(".txt", ".hash")
            if os.path.exists(hash_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    content = f.read()
                with open(hash_file, "r", encoding="utf-8") as f:
                    stored_hash = f.read().strip()
                content_bytes = content.encode("utf-8")
                computed_hash = hashlib.sha512(content_bytes).hexdigest()
                if computed_hash != stored_hash:
                    logger.error(f"External hash verification failed. Computed Hash: {computed_hash}, Stored Hash: {stored_hash}")
                    print(f"Error: Integrity verification failed for {output_file} with external hash.", flush=True)
                    print(f"Computed Hash: {computed_hash}", flush=True)
                    print(f"Stored Hash: {stored_hash}", flush=True)
                    print(f"Please remove {output_file} and {hash_file} and run the script again.", flush=True)
                    return False
                logger.info(f"Integrity verification passed using external .hash file.")
                print(f"Integrity verification passed for {output_file}.", flush=True)
                return True
            logger.warning(f"No valid hash found. Resuming from partial report.")
            print(f"Warning: No hash found for {output_file}. Resuming from partial report.", flush=True)
            return True
    except Exception as e:
        logger.error(f"Error verifying {output_file}: {str(e)}")
        print(f"Error verifying {output_file}: {str(e)}. Consider removing {output_file} to start over.", flush=True)
        return False

def read_existing_report(output_file):
    """Read existing report file to get processed model IDs and existing models, ignoring containers."""
    logger.info(f"Reading existing report: {output_file}")
    processed_model_ids = set()
    identifiable_model_ids = set()
    identifiable_models = []
    unrecognized_models = set()
    model_id_to_archive = {}
    if not os.path.exists(output_file):
        logger.info(f"No existing report found at {output_file}")
        return processed_model_ids, identifiable_models, list(unrecognized_models), identifiable_model_ids, model_id_to_archive

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
                parts = line.split(" - ", 2)
                if len(parts) == 3:
                    model_id_match = re.search(sky_regex, parts[0])
                    if model_id_match:
                        model_id = model_id_match.group(1)
                        model_type = parts[1].strip()
                        model_desc = parts[2].strip()
                        desc_parts = [part.strip() for part in model_desc.split("|")]
                        if len(desc_parts) >= 3:
                            processed_model_ids.add(model_id)
                            identifiable_model_ids.add(model_id)
                            is_pro = model_type == "Pro"
                            identifiable_models.append((f"{parts[0]} - {model_desc}", is_pro))
                            # Try each archive extension in order
                            archive_name = None
                            for ext in archive_extensions:
                                potential_archive = f"{model_id}{ext}"
                                # Check if the archive exists in the folder
                                for root, _, files in os.walk(os.path.dirname(output_file)):
                                    if potential_archive in files:
                                        archive_name = potential_archive
                                        break
                                if archive_name:
                                    break
                            if not archive_name:
                                archive_name = f"{model_id}.zip"  # Default to .zip if none found
                            model_id_to_archive[model_id] = archive_name
                            logger.debug(f"Loaded identifiable model: {model_id} (archive: {archive_name}, desc: {model_desc[:50]}...)")
                        else:
                            logger.warning(f"Skipping identifiable model with incomplete metadata: {line}")
                    else:
                        logger.warning(f"Skipping identifiable model with invalid model_id: {line}")
                else:
                    logger.warning(f"Skipping malformed identifiable model entry: {line}")
            elif current_section == "unrecognized" and line:
                if any(line.endswith(ext) or line.endswith(f"{ext} (no accompanying image)") for ext in archive_extensions):
                    unrecognized_models.add(line)
                    logger.debug(f"Loaded unrecognized model: {line}")
                else:
                    logger.warning(f"Skipping invalid unrecognized model entry: {line}")

    logger.info(f"Loaded {len(identifiable_models)} identifiable models, {len(unrecognized_models)} unrecognized models from {output_file}")
    logger.debug(f"Processed model IDs: {sorted(processed_model_ids)}")
    logger.debug(f"Identifiable model IDs: {sorted(identifiable_model_ids)}")
    logger.debug(f"Model ID to archive mapping: {model_id_to_archive}")
    return processed_model_ids, identifiable_models, list(unrecognized_models), identifiable_model_ids, model_id_to_archive

def write_report(output_file, all_identifiable_models, all_unrecognized_models, folder_name, is_final=False):
    """Write the report file with entries in [container] and hash in [hash_container]."""
    logger.info(f"Writing report to {output_file}")
    all_identifiable_models.sort(key=lambda x: numeric_sort_key(x[0]))
    pro_count = sum(1 for _, is_pro in all_identifiable_models if is_pro)
    free_count = len(all_identifiable_models) - pro_count
    total_identifiable = len(all_identifiable_models)
    total_unrecognized = len(all_unrecognized_models)

    lines = []
    header = (
        f"Sky-lister results: {total_identifiable} Identifiable "
        f"({pro_count} Pro and {free_count} FREE), "
        f"{total_unrecognized} Unrecognized/Non-Sky models in {folder_name}"
    )
    if not is_final:
        header += " (Partial Report)"
    header += "\n\n"
    lines.append(header)
    lines.append("Identifiable Sky Models:\n")
    for model, is_pro in all_identifiable_models:
        model_type = "Pro" if is_pro else "FREE"
        model_id, model_desc = model.split(" - ", 1)
        lines.append(f"{model_id} - {model_type: <4} - {model_desc}\n")
    lines.append("\nUnrecognized Sky Models (or missing image):\n")
    for model in all_unrecognized_models:
        lines.append(model + "\n")

    container_content = "".join(lines)
    content_bytes = container_content.encode("utf-8")
    integrity_hash = hashlib.sha512(content_bytes).hexdigest()
    logger.info(f"Computed SHA-512 hash for container content: {integrity_hash}")
    logger.debug(f"Container content length: {len(container_content)}, first 100 chars: {container_content[:100].replace('\n', '\\n')}")

    with open(output_file, "w", encoding="utf-8", newline="\n") as f:
        f.write("[container]\n")
        f.write(container_content)
        f.write("[/container]\n\n")
        f.write("[hash_container]\n")
        f.write(integrity_hash + "\n")
        f.write("[/hash_container]\n")
    logger.info(f"Report written to {output_file} with container and hash_container")

def process_folder(folder_path, source_folder, processed_model_ids, all_identifiable_models, all_unrecognized_models, output_file, folder_name, identifiable_model_ids, current_archives, model_id_to_archive):
    """Process a single folder: find archives, check model_id, and read metadata if needed."""
    logger.info(f"Scanning folder: {folder_path}")
    print(f"Scanning folder: {folder_path}", flush=True)
    
    archive_files = []
    new_identifiable_models = []
    new_unrecognized_models = set()
    
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path) and any(file.lower().endswith(ext) for ext in archive_extensions):
            archive_files.append(file_path)
            archive_basename = os.path.basename(file_path)
            logger.debug(f"Added archive to current_archives: {archive_basename} (extension: {os.path.splitext(file_path)[1]})")
            current_archives.add(archive_basename)
    
    logger.debug(f"Found {len(archive_files)} archives in {folder_path}: {[os.path.basename(p) for p in archive_files]}")
    
    for archive_path in archive_files:
        archive_basename = os.path.basename(archive_path)
        logger.info(f"Processing archive: {archive_path}")
        
        model_id = None
        for mid, arch in model_id_to_archive.items():
            if arch == archive_basename:
                model_id = mid
                break
        
        if model_id and model_id in processed_model_ids:
            logger.info(f"Skipping archive {archive_basename} via model_id_to_archive with model_id {model_id}: already processed")
            print(f"Skipping already processed model_id {model_id} for archive: {archive_basename}", flush=True)
            continue
        
        base_name = os.path.splitext(archive_path)[0]
        jpg_pattern = f"{base_name}.jpg"
        jpeg_pattern = f"{base_name}.jpeg"
        matching_images = glob(jpg_pattern) + glob(jpeg_pattern)
        logger.info(f"Found {len(matching_images)} matching images for {archive_path}: {matching_images}")
        
        if matching_images:
            first_image = sorted(matching_images)[0]
            logger.info(f"Processing archive: {archive_basename} (image: {first_image})")
            extracted_model_id = get_model_id(first_image)
            if extracted_model_id and extracted_model_id in identifiable_model_ids:
                logger.info(f"Skipping metadata read for {archive_basename}: model_id {extracted_model_id} already processed")
                print(f"Skipping already processed model_id {extracted_model_id} for archive: {archive_basename}", flush=True)
                continue
            logger.info(f"Performing new metadata read for {archive_basename} (image: {first_image})")
            result, is_pro, extracted_model_id = read_xmp_and_exif_data(first_image)
            if result and extracted_model_id and extracted_model_id not in identifiable_model_ids:
                identifiable_model_ids.add(extracted_model_id)
                new_identifiable_models.append((result, is_pro))
                model_id_to_archive[extracted_model_id] = archive_basename
                logger.info(f"Added new identifiable model: {result} (model_id: {extracted_model_id})")
                print(f"Added new identifiable model: {extracted_model_id} from {archive_basename}", flush=True)
            elif not result:
                new_unrecognized_models.add(archive_basename)
                logger.info(f"Marked as unrecognized: {archive_basename}")
        else:
            new_unrecognized_models.add(archive_basename + " (no accompanying image)")
            logger.info(f"Marked as unrecognized (no image): {archive_basename}")
    
    all_identifiable_models.extend(new_identifiable_models)
    all_unrecognized_models.extend([model for model in new_unrecognized_models if model not in set(all_unrecognized_models)])
    
    write_report(output_file, all_identifiable_models, all_unrecognized_models, folder_name)
    
    logger.info(f"Finished processing folder: {folder_path}")
    print(f"Finished processing folder: {folder_path}", flush=True)
    return new_identifiable_models, new_unrecognized_models

def generate_report(source_folder):
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

    processed_model_ids, all_identifiable_models, all_unrecognized_models, identifiable_model_ids, model_id_to_archive = read_existing_report(output_file)

    current_archives = set()

    process_folder(source_folder, source_folder, processed_model_ids, all_identifiable_models, all_unrecognized_models, output_file, folder_name, identifiable_model_ids, current_archives, model_id_to_archive)

    for root, dirs, _ in os.walk(source_folder):
        if root == source_folder:
            continue
        process_folder(root, source_folder, processed_model_ids, all_identifiable_models, all_unrecognized_models, output_file, folder_name, identifiable_model_ids, current_archives, model_id_to_archive)

    logger.debug(f"Current archives found in scan: {sorted(current_archives)}")
    logger.debug(f"Model ID to archive mapping: {model_id_to_archive}")

    filtered_identifiable_models = []
    removed_identifiable_models = []
    for model, is_pro in all_identifiable_models:
        model_id = model.split(" - ")[0].strip()
        archive_name = model_id_to_archive.get(model_id)
        if not archive_name:
            logger.warning(f"No archive mapped for model_id: {model_id}")
            removed_identifiable_models.append(f"{model_id} (no archive)")
            continue
        archive_path = None
        possible_archives = [f"{model_id}{ext}" for ext in archive_extensions]
        for potential_archive in possible_archives:
            for root, _, files in os.walk(source_folder):
                if potential_archive in files:
                    archive_path = os.path.join(root, potential_archive)
                    break
            if archive_path:
                archive_name = potential_archive
                break
        if archive_path and archive_name in current_archives:
            filtered_identifiable_models.append((model, is_pro))
            logger.debug(f"Kept identifiable model: {model_id} (archive: {archive_name})")
        else:
            removed_identifiable_models.append(f"{model_id} (archive: {archive_name}, path: {archive_path or 'not found'})")
            logger.info(f"Removed identifiable model: {model_id} (archive: {archive_name}, path: {archive_path or 'not found'}, tried: {possible_archives})")

    filtered_unrecognized_models = []
    removed_unrecognized_models = []
    for model in all_unrecognized_models:
        archive_name = model.split(" (")[0]
        archive_path = None
        for root, _, files in os.walk(source_folder):
            if archive_name in files:
                archive_path = os.path.join(root, archive_name)
                break
        if archive_path and archive_name in current_archives:
            filtered_unrecognized_models.append(model)
            logger.debug(f"Kept unrecognized model: {model}")
        else:
            removed_unrecognized_models.append(model)
            logger.info(f"Removed unrecognized model: {model} (path: {archive_path or 'not found'})")

    if removed_identifiable_models:
        logger.info(f"Removed {len(removed_identifiable_models)} identifiable models: {removed_identifiable_models}")
        print(f"Removed {len(removed_identifiable_models)} identifiable models no longer in folder: {removed_identifiable_models}", flush=True)
    if removed_unrecognized_models:
        logger.info(f"Removed {len(removed_unrecognized_models)} unrecognized models: {removed_unrecognized_models}")
        print(f"Removed {len(removed_unrecognized_models)} unrecognized models no longer in folder: {removed_unrecognized_models}", flush=True)

    write_report(output_file, filtered_identifiable_models, filtered_unrecognized_models, folder_name, is_final=True)
    logger.info(f"Report generation complete: {output_file}")
    print(f"Report generation complete: {output_file}", flush=True)

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
