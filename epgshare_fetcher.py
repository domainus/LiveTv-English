

import os
import requests
import gzip
import shutil
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz"
EPG_DIR = "./epg"

def download_and_extract_epg():
    """Download the EPG .gz file, extract it to .xml, and save in ./epg directory."""
    os.makedirs(EPG_DIR, exist_ok=True)

    file_name_gz = os.path.join(EPG_DIR, os.path.basename(EPG_URL))
    file_name_xml = file_name_gz.replace(".gz", "")

    logging.info(f"Downloading EPG file from {EPG_URL}")
    response = requests.get(EPG_URL, stream=True)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: {response.status_code}")

    with open(file_name_gz, "wb") as f:
        shutil.copyfileobj(response.raw, f)
    logging.info(f"Downloaded to {file_name_gz}")

    logging.info(f"Extracting {file_name_gz} to {file_name_xml}")
    with gzip.open(file_name_gz, "rb") as f_in:
        with open(file_name_xml, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    os.remove(file_name_gz)
    logging.info(f"Removed compressed file: {file_name_gz}")

    return file_name_xml

def commit_and_push(file_path):
    """Commit and push the extracted XML to GitHub."""
    logging.info("Committing and pushing updated EPG file to GitHub...")

    subprocess.run(["git", "add", file_path], check=True)
    subprocess.run(["git", "commit", "-m", f"Update EPG file: {os.path.basename(file_path)}"], check=True)
    subprocess.run(["git", "push"], check=True)

    logging.info("EPG file committed and pushed successfully.")

def main():
    try:
        xml_file = download_and_extract_epg()
        commit_and_push(xml_file)
    except Exception as e:
        logging.error(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()