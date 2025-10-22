import os
import requests
import gzip
import shutil
import logging

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

    logging.info(f"EPG extracted successfully to {file_name_xml}")
    return file_name_xml

def main():
    try:
        xml_file = download_and_extract_epg()
        # Output the XML path for GitHub Actions
        print(f"::set-output name=epg_file::{xml_file}")
    except Exception as e:
        logging.error(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()