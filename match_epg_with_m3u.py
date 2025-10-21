import re
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

EPG_FILE = "epg.xml"
M3U_FILE = "dlhd.m3u"
OUTPUT_FILE = "dlhd.m3u"

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

def match_channel_name(epg_mapping, line):
    """Try to find a channel name in M3U EXTINF line and return its tvg-id"""
    # Extract display name from EXTINF line
    match = re.search(r',([^,\n]+)$', line)
    if not match:
        return None
    display_name = match.group(1).strip().lower()

    # Simple direct match
    if display_name in epg_mapping:
        return epg_mapping[display_name]

    # Fuzzy fallback: check if any epg name appears inside the m3u name
    for epg_name, chan_id in epg_mapping.items():
        if epg_name in display_name:
            return chan_id
    return None

def main():
    epg_mapping = parse_epg(EPG_FILE)

    with open(M3U_FILE, "r", encoding="utf-8") as infile, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

        for line_number, line in enumerate(infile, 1):
            if line.startswith("#EXTINF"):
                logging.debug(f"Processing line {line_number}: {line.strip()}")
                tvg_match = re.search(r'tvg-id="([^"]+)"', line)
                if not tvg_match:
                    tvg_id = match_channel_name(epg_mapping, line)
                    if tvg_id:
                        # Insert tvg-id attribute before the comma
                        line = re.sub(
                            r'(#EXTINF:-1)',
                            rf'\1 tvg-id="{tvg_id}"',
                            line
                        )
                        logging.info(f"Added tvg-id '{tvg_id}' on line {line_number}.")
                    else:
                        logging.info(f"No matching tvg-id found for channel on line {line_number}.")
            outfile.write(line)

    logging.info(f"✅ Updated playlist written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()