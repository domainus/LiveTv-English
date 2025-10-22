import re
import xml.etree.ElementTree as ET
import logging
import os
import difflib
import unicodedata
import json

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

def update_epg_with_known_ids(epg_path, known_ids_path, output_path):
    """Update EPG channel ids based on known_channel_ids.json"""
    # Load known IDs JSON
    try:
        with open(known_ids_path, "r", encoding="utf-8") as f:
            known_ids = json.load(f)
    except Exception as e:
        logging.error(f"Failed to load known IDs JSON from {known_ids_path}: {e}")
        return

    # Read EPG content, handling .rtf by extracting XML content
    _, ext = os.path.splitext(epg_path.lower())
    xml_content = None
    try:
        if ext == ".rtf":
            with open(epg_path, "r", encoding="utf-8") as f:
                rtf_text = f.read()
            # Simple extraction of XML inside RTF: find first '<' and last '>'
            start = rtf_text.find("<")
            end = rtf_text.rfind(">")
            if start == -1 or end == -1 or end <= start:
                logging.error(f"Could not find XML content inside RTF file {epg_path}")
                return
            xml_content = rtf_text[start:end+1]
            root = ET.fromstring(xml_content)
        else:
            tree = ET.parse(epg_path)
            root = tree.getroot()
    except Exception as e:
        logging.error(f"Failed to parse EPG XML from {epg_path}: {e}")
        return

    # Build mapping from old ids to new ids
    old_to_new_id = {}

    # Iterate channels and update ids if display-name matches known ids
    for channel in root.findall("channel"):
        name_elem = channel.find("display-name")
        if name_elem is not None and name_elem.text:
            display_name_norm = name_elem.text.strip().lower()
            if display_name_norm in known_ids:
                old_id = channel.get("id")
                new_id = known_ids[display_name_norm]
                if old_id != new_id:
                    logging.info(f"Updating channel id for '{name_elem.text.strip()}': '{old_id}' -> '{new_id}'")
                    old_to_new_id[old_id] = new_id
                    channel.set("id", new_id)

    # Update programme elements channel attribute if matching old ids
    for programme in root.findall("programme"):
        ch = programme.get("channel")
        if ch in old_to_new_id:
            new_ch = old_to_new_id[ch]
            logging.info(f"Updating programme channel attribute: '{ch}' -> '{new_ch}'")
            programme.set("channel", new_ch)

    # Write updated XML to output_path
    try:
        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        logging.info(f"Updated EPG saved to {output_path}")
    except Exception as e:
        logging.error(f"Failed to write updated EPG XML to {output_path}: {e}")



if __name__ == "__main__":
    update_epg_with_known_ids("epg.xml", "known_channel_ids.json", "epg_updated.xml")