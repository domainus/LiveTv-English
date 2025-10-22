import re
from collections import defaultdict
import logging
import os
import difflib
import xml.etree.ElementTree as ET

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
        "pt": "Portugal", "prt": "Portugal", "portugal": "Portugal",
        "qa": "Qatar", "qatar": "Qatar",
        "il": "Israel", "isr": "Israel", "israel": "Israel",
        "ae": "UAE", "uae": "UAE", "arab": "Arab World", "arabic": "Arab World", "arabia": "Arab World",
        "afr": "Africa", "afrique": "Africa", "africa": "Africa", "mena": "Middle East & North Africa",
        "sa": "Saudi Arabia", "ksa": "Saudi Arabia", "saudi": "Saudi Arabia",
        "eg": "Egypt", "dz": "Algeria", "ma": "Morocco", "tn": "Tunisia",
        "jp": "Japan", "jpn": "Japan", "japan": "Japan",
        "kr": "South Korea", "kor": "South Korea", "korea": "South Korea",
        "in": "India", "ind": "India", "india": "India",
        "rs": "Serbia", "serbia": "Serbia",
        "hr": "Croatia", "croatia": "Croatia",
        "tr": "Turkey", "tur": "Turkey", "turkey": "Turkey",
        "bg": "Bulgaria", "bulgaria": "Bulgaria",
        "dk": "Denmark", "denmark": "Denmark",
        "ro": "Romania", "romania": "Romania",
        "gr": "Greece", "greece": "Greece",
        "pl": "Poland", "poland": "Poland",
        "se": "Sweden", "sw": "Sweden", "swe": "Sweden", "sweden": "Sweden",
        "nl": "Netherlands", "nld": "Netherlands", "netherlands": "Netherlands", "holland": "Netherlands",
        "ru": "Russia", "rus": "Russia", "russia": "Russia",
        "cz": "Czech Republic", "cze": "Czech Republic", "czech": "Czech Republic",
        "at": "Austria", "aut": "Austria", "austria": "Austria",
        "nz": "New Zealand", "nzl": "New Zealand", "new zealand": "New Zealand",
        "pk": "Pakistan", "pak": "Pakistan", "pakistan": "Pakistan",
        "ie": "Ireland", "irl": "Ireland", "ireland": "Ireland",
        "bundesliga": "Germany",
        "bosnia and herzegovina": "Bosnia and Herzegovina",
        "south africa": "South Africa",
        "hungary": "Hungary",
        "bangladesh": "Bangladesh",
        # Cyprus mappings
        "cy": "Cyprus", "cyp": "Cyprus", "cyprus": "Cyprus",
        # Australia mappings
        "au": "Australia", "aus": "Australia", "australia": "Australia"
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
    # --- Expanded USA channel/network map ---
    brand_map.update({
        # Fix incorrect categorization
        "universion": "Mexico",
        "sky history": "UK",
        # Major U.S. broadcast and cable networks
        "fox news": "USA", "msnbc": "USA", "cnn en español": "USA",
        "nbc news": "USA", "abc news": "USA", "cbs news": "USA",
        "fox business": "USA", "cnbc": "USA", "bloomberg": "USA",
        "espn2": "USA", "espn3": "USA", "espnews": "USA", "espn deportes": "USA",
        "fox sports 1": "USA", "fox sports 2": "USA", "fs1": "USA", "fs2": "USA",
        "nfl network": "USA", "nba tv": "USA", "mlb network": "USA", "nhl network": "USA",
        "discovery": "USA", "discovery channel": "USA", "science channel": "USA",
        "history": "USA", "history channel": "USA", "vice tv": "USA", "nat geo": "USA",
        "national geographic": "USA", "travel channel": "USA", "hgtv": "USA", "food network": "USA",
        "animal planet": "USA", "tlc": "USA", "bravo": "USA", "e!": "USA", "lifetime": "USA",
        "we tv": "USA", "own": "USA", "oxygen": "USA", "tru tv": "USA", "trutv": "USA",
        "tcm": "USA", "amc": "USA", "ifc": "USA", "sundance": "USA",
        "fxx": "USA", "fxm": "USA", "fox movies": "USA", "hallmark": "USA", "hallmark movies": "USA",
        "starz": "USA", "showtime": "USA", "hbo max": "USA", "hbo family": "USA", "hbo latino": "USA",
        "paramount network": "USA", "peacock": "USA", "apple tv": "USA", "apple tv+": "USA",
        "roku": "USA", "pluto tv": "USA", "tubi": "USA", "crackle": "USA", "sling": "USA", "fubo": "USA",
        "roku channel": "USA", "xumo": "USA", "hulu": "USA", "netflix": "USA", "disney+": "USA",
        "amazon prime": "USA", "prime video": "USA",
        # Kids / animation
        "nick jr": "USA", "nicktoons": "USA", "disney xd": "USA", "boomerang": "USA",
        "adult swim": "USA", "cartoonito": "USA", "pbs kids": "USA",
        # Music / culture
        "mtv2": "USA", "mtv live": "USA", "vh1": "USA", "bet": "USA", "cmt": "USA", "fuse": "USA",
        "revolt": "USA", "axs tv": "USA", "axs": "USA",
        # Regional / news / niche
        "newsmax": "USA", "one america news": "USA", "oann": "USA", "weather channel": "USA",
        "cw": "USA", "my network tv": "USA", "ion": "USA", "ion mystery": "USA", "me tv": "USA",
        "antenna tv": "USA", "cozi tv": "USA", "buzzr": "USA", "game show network": "USA", "gsn": "USA",
        "c-span": "USA", "c-span2": "USA", "c-span3": "USA",
        "tbn": "USA", "daystar": "USA", "eternity": "USA", "ewtn": "USA", "insp": "USA",
        "magnolia": "USA", "own": "USA",
        # Additional entries from dlhd.rtf
        "fanduel": "USA", "ahc": "USA", "cleotv": "USA", "c span": "USA", "law & crime": "USA",
        "headline news": "USA", "freeform": "USA", "motor trend": "USA", "reelz": "USA",
        "grit": "USA", "great american family": "USA", "altitude": "USA", "root sports": "USA",
        "space city": "USA", "nfl redzone": "USA", "tennis channel": "USA", "nick": "USA",
        "tvland": "USA", "fyi": "USA", "wwe": "USA",
        # UK
        "sky sports": "UK", "sky crime": "UK", "sky witness": "UK", "sky atlantic": "UK",
        "sky sports premier league": "UK", "sky sports main event": "UK", "sky sports cricket": "UK",
        "e4": "UK", "dave": "UK",
        # Malaysia
        "astro supersport": "Malaysia", "astro cricket": "Malaysia",
        # Qatar / Arab World
        "ssc sport": "Saudi Arabia", "alkass": "Qatar", "abu dhabi": "UAE",
        # Greece
        "cosmote": "Greece", "vodafone sport": "Greece",
        # South Africa
        "supersport": "South Africa", "dstv": "South Africa",
        # Romania
        "prima sport": "Romania",
        # Ireland
        "rte": "Ireland",
        # Netherlands
        "rtl": "Netherlands",
        # Spain
        "dazn laliga": "Spain", "movistar laliga": "Spain", "laliga": "Spain",
        # Hungary
        "m4 sports": "Hungary",
        # Pakistan
        "ptv sports": "Pakistan",
        # Bangladesh
        "t sports bd": "Bangladesh",
        # Sweden
        "tv4": "Sweden", "v film": "Sweden",
        # Canada
        "citytv": "Canada", "tva sports": "Canada",
        # Colombia
        "win sports": "Colombia",
        # France
        "automoto": "France",
        # Israel
        "channel 10 israel": "Israel",
        # Germany
        "sportdigital fussball": "Germany",
        # Serbia / Balkans
        "arena sport": "Serbia", "arena sport bih": "Bosnia and Herzegovina",
        "arena sport croatia": "Croatia", "arena sport premium": "Serbia"
    })

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

    # --- 5c) Priority region words override (prevents false USA classification) ---
    for keyword, country in {
        "argentina": "Argentina",
        "chile": "Chile",
        "uruguay": "Uruguay",
        "peru": "Peru",
        "colombia": "Colombia",
        "venezuela": "Venezuela",
        "ecuador": "Ecuador",
        "bolivia": "Bolivia",
        "paraguay": "Paraguay",
        "serbia": "Serbia",
        "croatia": "Croatia",
        "turkey": "Turkey",
        "bulgaria": "Bulgaria",
        "denmark": "Denmark",
        "portugal": "Portugal",
        "romania": "Romania",
        "greece": "Greece",
        "poland": "Poland",
        "sweden": "Sweden",
        "netherlands": "Netherlands",
        "holland": "Netherlands",
        "russia": "Russia",
        "czech": "Czech Republic",
        "austria": "Austria",
        "new zealand": "New Zealand",
        "pakistan": "Pakistan",
        "ireland": "Ireland",
        "bundesliga": "Germany",
        # Cyprus priority keyword
        "cyprus": "Cyprus",
        # Australia priority keyword
        "australia": "Australia"
    }.items():
        if keyword in display_normalized:
            logging.debug(f"Detected specific country keyword '{keyword}' overriding brand match")
            return country

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

    logging.info(f"Country not detected, marking as Other for line: {display}")
    return "Other"


def categorize_live_event(line):
    """
    Inspects the channel title and returns a more specific Live Events subcategory.
    """
    # Extract title from EXTINF line
    try:
        display = line.split(",", 1)[1].strip()
    except IndexError:
        display = line
    title = display.lower()
    # Normalize for keyword searching
    norm_title = re.sub(r'[^a-z0-9 ]', ' ', title)
    norm_title = re.sub(r'\s+', ' ', norm_title)
    # Soccer
    soccer_terms = [
        "soccer", "football", "liga", "champions", "world cup", "premier league",
        "serie a", "bundesliga", "laliga", "la liga", "uefa", "epl", "ligue 1", "copa", "mls"
    ]
    for sterm in soccer_terms:
        if sterm in norm_title:
            return "Live Events - All Soccer Matches"
    # NFL / American football
    if "nfl" in norm_title or "am. football" in norm_title:
        return "Live Events - Am. Football"
    # Basketball
    if "nba" in norm_title or "basketball" in norm_title:
        return "Live Events - Basketball"
    # Cricket
    if "cricket" in norm_title:
        return "Live Events - Cricket"
    # MMA
    if "ufc" in norm_title or "mma" in norm_title:
        return "Live Events - MMA"
    # Default
    return "Live Events - All Matches"


import json

def load_known_channel_ids(json_path="known_channel_ids.json"):
    """Load a dictionary of known canonical channel IDs (from IPTV-ORG schema)."""
    if not os.path.exists(json_path):
        logging.warning(f"Known ID file not found: {json_path}")
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Normalize keys for case-insensitive lookup
    return {k.lower(): v for k, v in data.items()}

def parse_epg(epg_path):
    """
    Parses an XMLTV EPG file and returns a mapping of channel id -> list of display-names.
    """
    epg_map = {}
    try:
        tree = ET.parse(epg_path)
        root = tree.getroot()
        for ch in root.findall("channel"):
            chid = ch.attrib.get("id", "").strip()
            names = [dn.text.strip() for dn in ch.findall("display-name") if dn.text and dn.text.strip()]
            if chid and names:
                epg_map[chid] = names
    except Exception as e:
        logging.error(f"Failed to parse EPG file {epg_path}: {e}")
    return epg_map

def find_best_epg_match(channel_name, epg_map):
    """
    Uses fuzzy matching to find the best EPG channel id for a given channel_name.
    Returns the best matching EPG id or None if no good match.
    """
    # Normalize channel name
    norm_name = channel_name.lower().strip()
    norm_name = re.sub(r'[^a-z0-9 ]', ' ', norm_name)
    norm_name = re.sub(r'\s+', ' ', norm_name).strip()
    best_score = 0
    best_id = None
    for chid, names in epg_map.items():
        for disp in names:
            disp_norm = disp.lower().strip()
            disp_norm = re.sub(r'[^a-z0-9 ]', ' ', disp_norm)
            disp_norm = re.sub(r'\s+', ' ', disp_norm).strip()
            score = difflib.SequenceMatcher(None, norm_name, disp_norm).ratio()
            if score > best_score:
                best_score = score
                best_id = chid
    # Consider only strong matches
    if best_score >= 0.85:
        return best_id
    return None


def organize_m3u_by_country(input_path, output_path):
    """
    Processes only DLHD 24/7 entries, groups them by country, and
    updates their group-title to the country name. Adds subcategories for Live Events.
    Integrates EPG channel ID matching if epg.xml is present.
    """
    logging.info(f"Reading input file: {input_path}")
    with open(input_path, "r", encoding="utf-8") as infile:
        lines = infile.readlines()
        
    known_ids = load_known_channel_ids()
    
    # Check for EPG file in the same directory
    epg_map = {}
    epg_matches = 0
    epg_path = os.path.join(os.path.dirname(os.path.abspath(input_path)), "epg.xml")
    if os.path.exists(epg_path):
        logging.info(f"EPG file detected: {epg_path}. Parsing for channel ID matching...")
        epg_map = parse_epg(epg_path)
        logging.info(f"EPG channels loaded: {len(epg_map)}")

    organized = defaultdict(list)
    live_events_categorized = defaultdict(list)  # For new live events subgroups
    current_extinf = None
    current_country = None
    total_processed = 0
    total_live_events = 0

    # Remove misplaced pre-loop EPG matching block (epg_id assignment before channel_name is defined)

    for idx, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            # Process entries with DLHD 24/7 or Live Event(s) in group-title
            if 'DLHD 24/7' in line or re.search(r'group-title="Live Events?"', line, re.IGNORECASE):
                extinf_line = line.strip()
                # Extract channel name for EPG matching
                try:
                    channel_name = extinf_line.split(",", 1)[1].strip()
                except IndexError:
                    channel_name = extinf_line
                # EPG ID matching: first try known_ids, then fuzzy EPG map if available
                epg_id = None
                if channel_name.lower() in known_ids:
                    epg_id = known_ids[channel_name.lower()]
                elif epg_map:
                    epg_id = find_best_epg_match(channel_name, epg_map)
                if epg_id:
                    # Inject or update tvg-id attribute
                    if re.search(r'tvg-id="[^"]*"', extinf_line):
                        extinf_line = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{epg_id}"', extinf_line)
                    else:
                        # Insert tvg-id before first comma or after first quote
                        m = re.search(r'(")([^"]*)(")', extinf_line)
                        if m:
                            # Insert tvg-id after the last quote in the attribute list
                            extinf_line = re.sub(r'(")([^"]*)(")', r'\1\2\3 tvg-id="' + epg_id + '"', extinf_line, count=1)
                        else:
                            # Fallback: before comma
                            extinf_line = extinf_line.replace(",", f' tvg-id="{epg_id}",', 1)
                    epg_matches += 1
                current_extinf = extinf_line
                current_country = extract_country(line)
                logging.debug(f"Processing channel '{line.strip()}' detected as {current_country}")
            else:
                logging.debug(f"Skipping non-DLHD 24/7/Live Event entry: {line.strip()}")
                current_extinf = None  # skip non-DLHD 24/7/Live Event entries
        elif line.strip() and not line.startswith("#"):
            # Found a stream URL
            if current_extinf:
                # Detect Live Events and categorize further
                if re.search(r'group-title="Live Events?"', current_extinf, re.IGNORECASE):
                    subcat = categorize_live_event(current_extinf)
                    live_events_categorized[subcat].append([current_extinf, line.strip()])
                    total_live_events += 1
                else:
                    organized[current_country].append([current_extinf, line.strip()])
                total_processed += 1

    logging.info(f"Number of countries found: {len(organized)}")
    logging.info(f"Total DLHD 24/7/Live Event channels processed: {total_processed}")
    logging.info(f"Total Live Event channels categorized: {total_live_events}")
    if epg_map:
        logging.info(f"Channels matched to EPG IDs: {epg_matches}")

    if total_processed == 0:
        logging.info("No DLHD 24/7 or Live Event channels found. No changes made to the output file.")
        return

    # Write output sorted by country and live event category
    logging.info(f"Writing grouped entries to output file: {output_path}")
    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.write("#EXTM3U\n\n")
        # Write DLHD 24/7 grouped by country
        for country in sorted(organized.keys()):
            for entry in organized[country]:
                extinf, url = entry
                # Only update group-title for DLHD 24/7, not Live Events
                new_extinf = re.sub(
                    r'group-title="[^"]*"',
                    f'group-title="{country}"',
                    extinf
                )
                outfile.write(new_extinf + "\n")
                outfile.write(url + "\n\n")
        # Write Live Events by subcategory, sorted by subcat name
        for subcat in sorted(live_events_categorized.keys()):
            for entry in live_events_categorized[subcat]:
                extinf, url = entry
                # Update group-title to include subcategory
                new_extinf = re.sub(
                    r'group-title="Live Events?"',
                    f'group-title="{subcat}"',
                    extinf,
                    flags=re.IGNORECASE
                )
                outfile.write(new_extinf + "\n")
                outfile.write(url + "\n\n")

    logging.info(f"✅ Filtered and organized DLHD 24/7 and Live Event channels written to {output_path}")

if __name__ == "__main__":
    organize_m3u_by_country(INPUT_FILE, OUTPUT_FILE)