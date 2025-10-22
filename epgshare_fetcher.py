import os
import requests
import shutil
import logging
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_URL = "https://epgshare01.online/epgshare01/"
EPG_DIR = "./epg"
MAX_SIZE_MB = 100

def get_epg_links():
    """Scrape BASE_URL for all .xml.gz links."""
    logging.info(f"Fetching available .xml.gz files from {BASE_URL}")
    response = requests.get(BASE_URL)
    if response.status_code != 200:
        raise Exception(f"Failed to access {BASE_URL} (status: {response.status_code})")

    soup = BeautifulSoup(response.text, "html.parser")
    links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith(".xml.gz")]
    logging.info(f"Found {len(links)} .xml.gz files.")
    return [BASE_URL + link for link in links]

def download_epg(epg_url):
    """Download .xml.gz file if under MAX_SIZE_MB."""
    os.makedirs(EPG_DIR, exist_ok=True)
    file_name_gz = os.path.join(EPG_DIR, os.path.basename(epg_url))

    # Check file size before downloading
    head = requests.head(epg_url)
    size = int(head.headers.get("Content-Length", 0)) / (1024 * 1024)
    if size > MAX_SIZE_MB:
        logging.warning(f"Skipping {epg_url} ({size:.2f} MB > {MAX_SIZE_MB} MB)")
        return None

    logging.info(f"Downloading {epg_url} ({size:.2f} MB)")
    response = requests.get(epg_url, stream=True)
    if response.status_code != 200:
        logging.warning(f"Failed to download {epg_url}")
        return None

    with open(file_name_gz, "wb") as f:
        shutil.copyfileobj(response.raw, f)
    logging.info(f"Saved to {file_name_gz}")

    return file_name_gz

def main():
    try:
        epg_links = get_epg_links()
        for link in epg_links:
            download_epg(link)
        logging.info("✅ All eligible compressed EPG files downloaded successfully.")
        logging.info("You can access them via raw GitHub URLs, e.g.:")
        logging.info("https://raw.githubusercontent.com/ryandriscoll/LiveTv-English/main/epg/epg_ripper_US1.xml.gz")
    except Exception as e:
        logging.error(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()