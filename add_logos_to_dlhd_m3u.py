

import os
import re
import difflib
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

LOGO_DIR = "./tv"
FALLBACK_LOGO = "./tv/logos/misc/24-7/circle1-247.png"
OUTPUT_FILE = "dlhd_with_logos.m3u"

def get_logo_files(base_dir):
    """Recursively get all logo files under the tv directory."""
    logo_map = {}
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                key = os.path.splitext(f)[0].lower()
                logo_map[key] = os.path.join(root, f)
    logging.info(f"Indexed {len(logo_map)} logos from {base_dir}")
    return logo_map

def best_logo_match(channel_name, logo_map):
    """Find best logo match using fuzzy matching with difflib."""
    normalized = re.sub(r'[^a-z0-9 ]', '', channel_name.lower())
    best = difflib.get_close_matches(normalized, logo_map.keys(), n=1, cutoff=0.7)
    if best:
        return logo_map[best[0]]
    # fallback
    return FALLBACK_LOGO

def add_logos_to_m3u(input_path, output_path):
    """Read M3U file, match each channel to a logo, and add tvg-logo attribute."""
    logos = get_logo_files(LOGO_DIR)
    with open(input_path, "r", encoding="utf-8") as infile:
        lines = infile.readlines()

    output_lines = []
    match_count = 0
    fallback_count = 0

    for line in lines:
        if line.startswith("#EXTINF"):
            # Extract channel name after comma
            match = re.search(r",(.+)", line)
            if match:
                channel_name = match.group(1).strip()
                logo_path = best_logo_match(channel_name, logos)
                if logo_path == FALLBACK_LOGO:
                    fallback_count += 1
                else:
                    match_count += 1

                if 'tvg-logo="' in line:
                    new_line = re.sub(r'tvg-logo="[^"]*"', f'tvg-logo="{logo_path}"', line)
                else:
                    new_line = line.strip().replace(",", f'" tvg-logo="{logo_path}",', 1)
                output_lines.append(new_line + "\n")
            else:
                output_lines.append(line)
        else:
            output_lines.append(line)

    with open(output_path, "w", encoding="utf-8") as outfile:
        outfile.writelines(output_lines)

    logging.info(f"✅ Completed logo matching. Matched: {match_count}, Fallbacks: {fallback_count}")
    logging.info(f"Output written to {output_path}")

if __name__ == "__main__":
    input_file = input("Enter input .m3u file path: ").strip()
    if not os.path.exists(input_file):
        logging.error(f"File not found: {input_file}")
        exit(1)
    add_logos_to_m3u(input_file, OUTPUT_FILE)