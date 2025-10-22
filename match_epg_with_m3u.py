import re
import xml.etree.ElementTree as ET
import logging
import os
import difflib
import unicodedata

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

EPG_FILE = "epg.xml"
M3U_FILE = "dlhd.m3u"
OUTPUT_FILE = "dlhd_match_to_epg.m3u"

# Prevent accidental overwrite of the source playlist
if os.path.abspath(M3U_FILE) == os.path.abspath(OUTPUT_FILE):
    base, ext = os.path.splitext(M3U_FILE)
    OUTPUT_FILE = f"{base}_matched{ext}"
    logging.warning(f"Output file matches source! Redirecting output to: {OUTPUT_FILE}")

logging.info(f"Reading from {os.path.abspath(M3U_FILE)}")
logging.info(f"Writing to {os.path.abspath(OUTPUT_FILE)}")

def parse_epg(epg_path):
    """Parse EPG XML and return a dict of display-name -> id"""
    tree = ET.parse(epg_path)
    root = tree.getroot()
    mapping = {}
    for channel in root.findall("channel"):
        chan_id = channel.get("id")
        name_elem = channel.find("display-name")
        if name_elem is not None and name_elem.text:
            display_name = name_elem.text.strip().lower()
            mapping[display_name] = chan_id
    logging.info(f"Parsed {len(mapping)} channels from EPG.")
    return mapping

def normalize(s):
    """Normalize and clean up channel names for better fuzzy matching"""
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("utf-8")
    s = s.replace("&", "and")
    s = s.replace("+", "plus")
    s = s.replace("hd", "").replace("fhd", "").replace("uhd", "")
    s = re.sub(r'\b(tv|channel|sports?|network|extra|premium|international|world|the)\b', '', s)
    s = re.sub(r'[^a-z0-9]+', '', s)
    return s.strip()

ALIASES = {
    "sky sports plus": "sky sports+",
    "tnt sports": "tnt_sports_1_uk",
    "bein mena": "bein_sports_mena_1",
    "movistar liga campeones": "movistar_liga_de_campeones",
    "sportklub croatia": "sportklub_1_croatia",
    "sportklub serbia": "sportklub_1_serbia",
    "arena sport serbia": "arena_sport_1_serbia",
    "arena sport croatia": "arena_sport_1_croatia",
    "nova sport cz": "nova_sport_cz",
    "nova sport 1": "nova_sport_1_cz",
    "nova sport 2": "nova_sport_2_cz",
}

def match_channel_name(epg_mapping, line):
    """Try to find a channel name in M3U EXTINF line and return its tvg-id"""
    match = re.search(r',([^,\n]+)$', line)
    if not match:
        return None
    display_name = match.group(1).strip()
    display_norm = normalize(display_name)

    # Pre-index normalized EPG mapping for performance
    if not hasattr(match_channel_name, "epg_index"):
        match_channel_name.epg_index = {normalize(k): v for k, v in epg_mapping.items()}

    # Check aliases first
    for alias, real in ALIASES.items():
        if alias in display_norm:
            for epg_name, chan_id in epg_mapping.items():
                if real in epg_name:
                    logging.debug(f"Alias match: {display_name} -> {epg_name}")
                    return chan_id

    # 1️⃣ Exact normalized match
    if display_norm in match_channel_name.epg_index:
        return match_channel_name.epg_index[display_norm]

    # 2️⃣ Partial substring containment
    for epg_norm, chan_id in match_channel_name.epg_index.items():
        if epg_norm in display_norm or display_norm in epg_norm:
            logging.debug(f"Partial match: '{display_name}' -> '{epg_norm}'")
            return chan_id

    # 3️⃣ Fuzzy similarity threshold
    best_match, best_ratio = None, 0
    for epg_norm, chan_id in match_channel_name.epg_index.items():
        ratio = difflib.SequenceMatcher(None, display_norm, epg_norm).ratio()
        if ratio > best_ratio:
            best_match, best_ratio = chan_id, ratio

    if best_ratio >= 0.72:  # adjustable similarity threshold
        return best_match

    logging.debug(f"No match for '{display_name}' (normalized: {display_norm})")
    return None

def main():
    epg_mapping = parse_epg(EPG_FILE)

    tvg_id_added_count = 0
    lines = []

    with open(M3U_FILE, "r", encoding="utf-8") as infile:
        for line_number, line in enumerate(infile, 1):
            if line.startswith("#EXTINF"):
                logging.debug(f"Processing line {line_number}: {line.strip()}")
                tvg_match = re.search(r'tvg-id="([^"]+)"', line)
                if not tvg_match:
                    tvg_id = match_channel_name(epg_mapping, line)
                    if tvg_id:
                        line = re.sub(
                            r'(#EXTINF:-1)',
                            rf'\1 tvg-id="{tvg_id}"',
                            line
                        )
                        tvg_id_added_count += 1
                        logging.info(f"Added tvg-id '{tvg_id}' on line {line_number}.")
                    else:
                        logging.info(f"No matching tvg-id found for channel on line {line_number}.")
            lines.append(line)

    if tvg_id_added_count == 0:
        logging.warning("⚠️ No tvg-id entries were added. Writing diagnostic output file for inspection.")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
            outfile.writelines(lines)
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        outfile.writelines(lines)

    logging.info(f"✅ Updated playlist written to {OUTPUT_FILE} with {tvg_id_added_count} tvg-ids added.")

if __name__ == "__main__":
    main()