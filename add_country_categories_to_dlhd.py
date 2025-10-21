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
    Extract a country name from an EXTINF line using multiple strategies.
    Priority:
      1) tvg-country attribute if present
      2) After a pipe (|), take the token that looks like a country, optionally before '-' or ':'
      3) Search for known country names/aliases in the display name segment
    Returns a normalized country name or 'Unknown'.
    """
    # Known countries and aliases (extend as needed)
    aliases = {
        "u.s.a": "USA",
        "us": "USA",
        "usa": "USA",
        "united states": "USA",
        "u.s": "USA",
        "uk": "UK",
        "united kingdom": "UK",
        "england": "UK",  # common shorthand
        "u.a.e": "UAE",
        "uae": "UAE",
        "k.s.a": "Saudi Arabia",
        "ksa": "Saudi Arabia",
        "saudi": "Saudi Arabia",
        "saudi arabia": "Saudi Arabia",
        "korea": "South Korea",  # heuristic
        "south korea": "South Korea",
        "s. korea": "South Korea",
        "n. korea": "North Korea",
        "north korea": "North Korea",
        "u.s.s.r": "Russia",
        "russia": "Russia",
        "russian federation": "Russia",
        "japan": "Japan",
        "germany": "Germany",
        "de": "Germany",
        "ger": "Germany",
        "german": "Germany",
        "france": "France",
        "spain": "Spain",
        "es": "Spain",
        "mexico": "Mexico",
        "canada": "Canada",
        "brazil": "Brazil",
        "argentina": "Argentina",
        "italy": "Italy",
        "it": "Italy",
        "portugal": "Portugal",
        "pt": "Portugal",
        "netherlands": "Netherlands",
        "nl": "Netherlands",
        "holland": "Netherlands",
        "turkey": "Turkey",
        "india": "India",
        "pakistan": "Pakistan",
        "bangladesh": "Bangladesh",
        "nepal": "Nepal",
        "sri lanka": "Sri Lanka",
        "china": "China",
        "taiwan": "Taiwan",
        "hong kong": "Hong Kong",
        "singapore": "Singapore",
        "indonesia": "Indonesia",
        "malaysia": "Malaysia",
        "philippines": "Philippines",
        "thailand": "Thailand",
        "vietnam": "Vietnam",
        "australia": "Australia",
        "new zealand": "New Zealand",
        "ireland": "Ireland",
        "scotland": "UK",
        "wales": "UK",
        "poland": "Poland",
        "pl": "Poland",
        "romania": "Romania",
        "ro": "Romania",
        "greece": "Greece",
        "gr": "Greece",
        "sweden": "Sweden",
        "se": "Sweden",
        "norway": "Norway",
        "no": "Norway",
        "denmark": "Denmark",
        "dk": "Denmark",
        "finland": "Finland",
        "fi": "Finland",
        "iceland": "Iceland",
        "switzerland": "Switzerland",
        "ch": "Switzerland",
        "austria": "Austria",
        "aut": "Austria",
        "at": "Austria",
        "belgium": "Belgium",
        "be": "Belgium",
        "portuguese": "Portugal",
        "kurdistan": "Kurdistan",
        "israel": "Israel",
        "egypt": "Egypt",
        "morocco": "Morocco",
        "algeria": "Algeria",
        "tunisia": "Tunisia",
        "south africa": "South Africa",
        "bulgaria": "Bulgaria",
        "bulgeria": "Bulgaria",
        "bg": "Bulgaria",
        "cz": "Czech Republic",
        "czech": "Czech Republic",
        "hun": "Hungary",
        "hu": "Hungary",
        "hr": "Croatia",
        "croatia": "Croatia",
        "rs": "Serbia",
        "serbia": "Serbia",
        "sk": "Slovakia",
        "slovakia": "Slovakia",
        "ua": "Ukraine",
        "ukraine": "Ukraine",
        "by": "Belarus",
        "belarus": "Belarus",
        "lt": "Lithuania",
        "lv": "Latvia",
        "ee": "Estonia",
        "si": "Slovenia",
    }

    # 1) tvg-country attribute
    m = re.search(r'tvg-country="([^"]+)"', line, flags=re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        key = re.sub(r"[^a-z]+", " ", val.lower()).strip()
        if key in aliases:
            return aliases[key]
        # If attribute looks like a country name, return it raw
        if len(val) >= 2:
            return val

    # Extract display name (after the comma)
    try:
        display = line.split(',', 1)[1].strip()
    except IndexError:
        display = line

    # 2) Prefer the part after a pipe (common DLHD pattern: "DLHD | <Country> - <Channel>")
    post_pipe = display.split('|', 1)[1].strip() if '|' in display else display

    # If we have a clear delimiter after country
    m2 = re.search(r'^\s*([A-Za-z .\'\/()-]+?)\s*[-:]', post_pipe)
    if m2:
        candidate = m2.group(1).strip()
        key = re.sub(r"[^a-z]+", " ", candidate.lower()).strip()
        if key in aliases:
            return aliases[key]
        if candidate and candidate.lower() not in {"dlhd", "live events"}:
            return candidate

    # 3) No delimiter. Try to detect a country token inside post_pipe or display
    def detect_country(text):
        low = text.lower()
        # Normalize punctuation to spaces, collapse
        norm = re.sub(r"[^a-z0-9]+", " ", low).strip()
        # Check full-string alias match
        if norm in aliases:
            return aliases[norm]
        # Check word-by-word matches and 2-word phrases
        words = norm.split()
        # Check bigrams first (e.g., "united states")
        for i in range(len(words)-1):
            phrase = f"{words[i]} {words[i+1]}"
            if phrase in aliases:
                return aliases[phrase]
        # Then unigrams (e.g., "usa")
        for w in words:
            if w in aliases:
                return aliases[w]
        # Heuristic: last token like "USA" at end (as in "ABC USA")
        last = words[-1] if words else ""
        if last in aliases:
            return aliases[last]
        return None

    for txt in (post_pipe, display):
        detected = detect_country(txt)
        if detected:
            return detected

    # Heuristic fallback: known brands strongly tied to a specific country
    brand_map = {
        "comedy central": "USA",
        "hbo": "USA",
        "nbc": "USA",
        "fox": "USA",
        "abc": "USA",
        "cbs": "USA",
        "espn": "USA",
        "cnn": "USA",
        "tnt": "USA",
        "mtv": "USA",
        "cartoon network": "USA",
        "nickelodeon": "USA",
        "disney": "USA",
        "univision": "USA",
        "telemundo": "USA",
        "sky sport de": "Germany",
        "sky deutschland": "Germany",
        "rtl": "Germany",
        "pro7": "Germany",
        "sat1": "Germany",
        "orf": "Austria",
        "nova bg": "Bulgaria",
        "bt sport": "UK",
        "sky uk": "UK",
        "bbc": "UK"
    }
    text_lower = post_pipe.lower()
    for brand, country in brand_map.items():
        if brand in text_lower:
            return country

    # 4) Fallback
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