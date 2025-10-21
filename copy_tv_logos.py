

import os
import subprocess
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REPO_URL = "https://github.com/tv-logo/tv-logos.git"
DEST_DIR = "./tv_logos_repo"
OUTPUT_DIR = "./tv/logos"

def clone_repo():
    """Clone or update the GitHub repository."""
    if os.path.exists(DEST_DIR):
        logging.info("Repository already exists. Updating...")
        try:
            subprocess.run(["git", "-C", DEST_DIR, "pull"], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to update repository: {e}")
            return False
    else:
        logging.info(f"Cloning repository from {REPO_URL}")
        try:
            subprocess.run(["git", "clone", "--depth", "1", REPO_URL, DEST_DIR], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to clone repository: {e}")
            return False
    return True

def copy_folders():
    """Copy all folders from the cloned repository to OUTPUT_DIR."""
    if not os.path.exists(DEST_DIR):
        logging.error("Repository not found. Please clone it first.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for item in os.listdir(DEST_DIR):
        src_path = os.path.join(DEST_DIR, item)
        dst_path = os.path.join(OUTPUT_DIR, item)
        if os.path.isdir(src_path):
            logging.info(f"Copying folder: {item}")
            if os.path.exists(dst_path):
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
        else:
            logging.debug(f"Skipping non-folder: {item}")

if __name__ == "__main__":
    if clone_repo():
        copy_folders()
        logging.info("✅ All folders have been copied successfully.")
    else:
        logging.error("❌ Repository cloning failed.")