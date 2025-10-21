import re
from collections import defaultdict
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

COUNTRY_ATTR_RE = re.compile(r'tvg-country="([^"]+)"', re.IGNORECASE)
COUNTRY_DELIM_RE = re.compile(r'^\s*([A-Za-z .\'\/()-]+?)\s*[-:]', re.IGNORECASE)
UPPER_CODE_RE = re.compile(r"\b[A-Z]{2,3}\b")

INPUT_FILE = "dlhd_match_to_epg.m3u"
OUTPUT_FILE = "dlhd_with_country_categories.m3u"

def extract_country(line):
    """Extract and normalize the country name for a DLHD channel line."""
    # --- Aliases ---
    aliases = {
        # Core mappings
        "us": "USA", "usa": "USA", "u.s.a": "USA", "united states": "USA", "u.s": "USA",
        "uk": "UK", "united kingdom": "UK", "england": "UK", "scotland": "UK", "wales": "UK",
        "br": "Brazil", "brasil": "Brazil", "brazil": "Brazil",
        "ca": "Canada", "can": "Canada", "canada": "Canada",
        "de": "Germany", "ger": "Germany", "germany": "Germany",
        "mx": "Mexico", "mex": "Mexico", "mexico": "Mexico",
        "fr": "France", "fra": "France", "france": "France",
        "es": "Spain", "esp": "Spain", "spain": "Spain",
        "it": "Italy", "ita": "Italy", "italy": "Italy",
        "pt": "Portugal", "portuguese": "Portugal",
        "qa": "Qatar", "qatar": "Qatar",
        "il": "Israel", "isr": "Israel", "israel": "Israel",
        "ae": "UAE", "uae": "UAE", "arab": "Arab World", "arabic": "Arab World", "arabia": "Arab World",
        "afr": "Africa", "afrique": "Africa", "africa": "Africa", "mena": "Middle East & North Africa",
        "sa": "Saudi Arabia", "ksa": "Saudi Arabia", "saudi": "Saudi Arabia",
        "eg": "Egypt", "dz": "Algeria", "ma": "Morocco", "tn": "Tunisia",
        "jp": "Japan", "jpn": "Japan", "japan": "Japan",
        "kr": "South Korea", "kor": "South Korea", "korea": "South Korea",
        "in": "India", "ind": "India", "india": "India"
    }

    # --- Brand heuristics ---
    brand_map = {
        # USA
        "adult swim": "USA", "tbs": "USA", "tnt": "USA", "fx": "USA", "syfy": "USA",
        "paramount": "USA", "hbo": "USA", "showtime": "USA", "fox": "USA", "espn": "USA",
        "cnn": "USA", "c-span": "USA", "comedy central": "USA", "pbs": "USA",
        "nbc": "USA", "abc": "USA", "cbs": "USA", "cw": "USA", "disney": "USA",
        "nickelodeon": "USA", "mtv": "USA", "cartoon network": "USA", "cnn international": "USA",
        # Canada
        "cbc": "Canada", "cbc ca": "Canada", "ctv": "Canada", "global": "Canada", "tsn": "Canada",
        "sportsnet": "Canada",
        # Brazil
        "rede globo": "Brazil", "globo": "Brazil", "band": "Brazil", "record tv": "Brazil",
        "sportv": "Brazil",
        # Mexico
        "televisa": "Mexico", "azteca": "Mexico", "multimedios": "Mexico",
        # Israel
        "kan": "Israel", "sport 5": "Israel", "i24": "Israel",
        # Qatar
        "bein": "Qatar", "al jazeera": "Qatar",
        # UK
        "bbc": "UK", "itv": "UK", "sky uk": "UK", "bt sport": "UK",
        # France
        "canal+": "France", "tf1": "France", "france 24": "France", "tv5": "France",
        # Africa / Arab
        "mbc": "Arab World", "rotana": "Arab World", "dubai one": "Arab World",
        "africanews": "Africa", "trace": "Africa", "afrique": "Africa"
    }

    # --- 1) tvg-country ---
    m = COUNTRY_ATTR_RE.search(line)
    if m:
        val = m.group(1).strip().lower()
        key = re.sub(r"[^a-z]+", " ", val)
        if key in aliases:
            return aliases[key]
        return val.title()

    # --- 2) Extract display segment ---
    try:
        display = line.split(",", 1)[1].strip()
    except IndexError:
        display = line
    post_pipe = display.split("|", 1)[1].strip() if "|" in display else display

    # --- Normalize display name ---
    display_normalized = display.strip().lower()
    # Remove punctuation and special characters except spaces
    display_normalized = re.sub(r'[^a-z0-9\s]', ' ', display_normalized)
    # Collapse multiple spaces
    display_normalized = re.sub(r'\s+', ' ', display_normalized).strip()

    # --- 3) Country prefix detection ---
    m2 = COUNTRY_DELIM_RE.search(post_pipe)
    if m2:
        candidate = m2.group(1).strip().lower()
        key = re.sub(r"[^a-z]+", " ", candidate)
        if key in aliases:
            return aliases[key]

    # --- 4) Token scanning ---
    norm = display_normalized
    words = norm.split()
    for i in range(len(words)):
        single = words[i]
        if single in aliases:
            return aliases[single]
        if i < len(words)-1:
            phrase = f"{words[i]} {words[i+1]}"
            if phrase in aliases:
                return aliases[phrase]

    # --- 5) Uppercase country codes like [MX], (QA), etc. ---
    for t in UPPER_CODE_RE.findall(display_normalized):
        key = t.lower()
        if key in aliases:
            return aliases[key]

    # --- Suffix detection for normalized lowercase country code at end ---
    suffix_match = re.search(r"\b([a-z]{2,3})\b$", display_normalized)
    if suffix_match:
        key = suffix_match.group(1)
        if key in aliases:
            return aliases[key]

    # --- 6) Brand heuristic ---
    text_lower = post_pipe.lower()
    for brand, country in brand_map.items():
        if brand in text_lower:
            return country

    # --- 7) Script-based heuristics ---
    if re.search(r"[\u0600-\u06FF]", display):  # Arabic
        return "Arab World"
    if re.search(r"[\u4E00-\u9FFF]", display):  # Chinese
        return "China"
    if re.search(r"[\u3040-\u30FF]", display):  # Japanese
        return "Japan"
    if re.search(r"[\uAC00-\uD7AF]", display):  # Korean
        return "South Korea"
    if re.search(r"[\u0400-\u04FF]", display):  # Cyrillic
        return "Russia"

    logging.info(f"Country not detected, marking as Unknown for line: {display}")
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
            # Process only entries with DLHD 24/7 anywhere in group-title
            if 'DLHD 24/7' in line:
                current_extinf = line.strip()
                current_country = extract_country(line)
                logging.debug(f"Processing channel '{line.strip()}' detected as {current_country}")
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