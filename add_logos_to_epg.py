import os
import xml.etree.ElementTree as ET
import requests
import logging
import json

# --- CONFIGURATION ---
EPG_FILE = "epg.xml"
LOGO_BASE_URL = "https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/"
OUTPUT_FILE = "epg.xml"
CACHE_FILE = "logo_cache.json"

# Optional: local logo directory for fallback
LOCAL_LOGO_DIR = ""  # leave empty if not used

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load cache file: {e}")
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        logging.warning(f"Failed to save cache file: {e}")

import difflib
import re

def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[\s_\-]+', '', name)
    name = name.replace('&', 'and').replace('+', 'plus')
    name = name.replace('hd', '').replace('fhd', '').replace('uhd', '')
    name = re.sub(r'\b(tv|channel|network|sports?|extra|international|premium|the)\b', '', name)
    return name.strip()

GITHUB_LOGO_BASE = "https://raw.githubusercontent.com/ryandriscoll/LiveTv-English/main/tv/"

def to_github_url(local_path):
    rel_path = os.path.relpath(local_path, "./tv").replace("\\", "/")
    return f"{GITHUB_LOGO_BASE}{rel_path}"

def find_logo(channel_id, channel_name, cache):
    """
    Find a logo in ./tv recursively using intelligent name matching.
    Uses normalized comparisons, substring checks, and fuzzy similarity scoring before falling back.
    """
    base_dir = "./tv"
    logo_filename = f"{channel_id}.png"

    # Check cache first
    if channel_id in cache:
        cached = cache[channel_id]
        path = cached.get("url")
        if path and os.path.exists(path.replace("file://", "")):
            return path

    # Build index of available logos
    available = []
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".png"):
                available.append((f, os.path.join(root, f)))

    id_norm = normalize_name(channel_id)
    name_norm = normalize_name(channel_name)

    # 1️⃣ Exact filename match
    for f, path in available:
        if normalize_name(os.path.splitext(f)[0]) == id_norm:
            return to_github_url(path)

    # 2️⃣ Partial substring match
    for f, path in available:
        fnorm = normalize_name(os.path.splitext(f)[0])
        if id_norm in fnorm or name_norm in fnorm:
            return to_github_url(path)

    # 3️⃣ Fuzzy similarity (difflib)
    candidates = {normalize_name(os.path.splitext(f)[0]): path for f, path in available}
    best_match = None
    best_ratio = 0
    for fnorm, path in candidates.items():
        ratio = difflib.SequenceMatcher(None, id_norm or name_norm, fnorm).ratio()
        if ratio > best_ratio:
            best_match, best_ratio = path, ratio

    if best_match and best_ratio >= 0.7:
        return to_github_url(best_match)

    # 4️⃣ Fallback logo
    misc_fallback = "./tv/logos/misc/circle1-247.png"
    if os.path.exists(misc_fallback):
        logging.warning(f"No suitable match found for {channel_id}, using backup logo.")
        logo_url = to_github_url(misc_fallback)
    else:
        logo_url = ""
    return logo_url


def main():
    cache = load_cache()

    tree = ET.parse(EPG_FILE)
    root = tree.getroot()

    count_added = 0
    for channel in root.findall("channel"):
        chan_id = channel.get("id")
        chan_name = channel.get("name", "") or ""
        logo_url = find_logo(chan_id, chan_name, cache)

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

    # Save updated cache including fallback entries
    save_cache(cache)
    logging.info(f"Saved {len(cache)} entries to cache (including fallbacks).")


if __name__ == "__main__":
    main()