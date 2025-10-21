import re
from collections import defaultdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

INPUT_FILE = "dlhd_match_to_epg.m3u"
OUTPUT_FILE = "dlhd_with_country_categories.m3u"

def extract_country(line):
    """
    Extract country name from the display name part of the EXTINF line.
    Example:
      "#EXTINF:-1 group-title=\"DLHD 24/7\",DLHD | Japan - Fuji TV"
    Returns: "Japan"
    """
    match = re.search(r'\|\s*([^|:-]+?)\s*[-:]', line)
    if match:
        country = match.group(1).strip()
        if not country or country.lower() in {"dlhd", "live events"}:
            return "Unknown"
        return country
    return "Unknown"

def organize_m3u_by_country(input_path, output_path):
    """
    Processes only DLHD 24/7 entries, groups them by country, and
    updates their group-title to the country name.
    """
    logging.info(f"Reading input file: {input_path}")
    with open(input_path, "r", encoding="utf-8") as infile:
        lines = infile.readlines()

    organized = defaultdict(list)
    current_extinf = None
    current_country = None
    total_processed = 0

    for line in lines:
        if line.startswith("#EXTINF"):
            # Process only entries with DLHD 24/7
            if 'group-title="DLHD 24/7"' in line:
                current_extinf = line.strip()
                current_country = extract_country(line)
                logging.info(f"Processing channel with country: {current_country}")
            else:
                logging.debug(f"Skipping non-DLHD 24/7 entry: {line.strip()}")
                current_extinf = None  # skip non-DLHD 24/7 entries
        elif line.strip() and not line.startswith("#"):
            # Found a stream URL
            if current_extinf:
                organized[current_country].append([current_extinf, line.strip()])
                total_processed += 1

    logging.info(f"Number of countries found: {len(organized)}")
    logging.info(f"Total DLHD 24/7 channels processed: {total_processed}")

    if total_processed == 0:
        logging.info("No DLHD 24/7 channels found. No changes made to the output file.")
        return

    # Write output sorted by country
    logging.info(f"Writing grouped entries to output file: {output_path}")
    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.write("#EXTM3U\n\n")
        for country in sorted(organized.keys()):
            for entry in organized[country]:
                extinf, url = entry
                new_extinf = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{country}"',
                    extinf
                )
                outfile.write(new_extinf + "\n")
                outfile.write(url + "\n\n")

    logging.info(f"✅ Filtered and organized DLHD 24/7 channels written to {output_path}")

if __name__ == "__main__":
    organize_m3u_by_country(INPUT_FILE, OUTPUT_FILE)