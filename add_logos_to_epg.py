import os
import xml.etree.ElementTree as ET
import requests
import logging

# --- CONFIGURATION ---
EPG_FILE = "epg.xml"
LOGO_BASE_URL = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/"
OUTPUT_FILE = "epg.xml"

# Optional: local logo directory for fallback
LOCAL_LOGO_DIR = ""  # leave empty if not used

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def find_logo(channel_id):
    """
    Try to find a logo for a given channel ID.
    Search across all country subdirectories under the base URL.
    """
    logo_filename = f"{channel_id}.png"

    # Get list of countries by scraping the GitHub directory listing
    countries_url = LOGO_BASE_URL
    try:
        response = requests.get("https://api.github.com/repos/tv-logo/tv-logos/contents/countries")
        if response.status_code == 200:
            countries = [entry['name'] for entry in response.json() if entry['type'] == 'dir']
        else:
            logging.warning(f"Failed to fetch countries list, status code: {response.status_code}")
            countries = []
    except Exception as e:
        logging.error(f"Exception occurred while fetching countries: {e}")
        countries = []

    # Try each country URL to find the logo
    for country in countries:
        logo_url = f"{LOGO_BASE_URL}{country}/{logo_filename}"
        # Check if the logo exists (HEAD request)
        try:
            head_resp = requests.head(logo_url)
            if head_resp.status_code == 200:
                logging.info(f"Logo found at {logo_url}")
                return logo_url
        except Exception as e:
            logging.warning(f"Exception during HEAD request to {logo_url}: {e}")
            continue

    # If not found, return the logo URL in the 'us' directory as fallback
    fallback_url = f"{LOGO_BASE_URL}us/{logo_filename}"
    logging.info(f"Logo not found in other countries, using fallback: {fallback_url}")
    return fallback_url


def main():
    tree = ET.parse(EPG_FILE)
    root = tree.getroot()

    count_added = 0
    for channel in root.findall("channel"):
        chan_id = channel.get("id")
        logo_url = find_logo(chan_id)

        # Check if <icon> already exists
        icon = channel.find("icon")
        if icon is None:
            icon = ET.SubElement(channel, "icon")
            icon.set("src", logo_url)
            count_added += 1
        else:
            icon.set("src", logo_url)

    tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)
    logging.info(f"Added/updated logos for {count_added} channels.")
    logging.info(f"Output saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()