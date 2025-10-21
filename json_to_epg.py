import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# ---- CONFIGURATION ----
INPUT_FILE = "daddyliveSchedule.json"
OUTPUT_FILE = "epg.xml"
TIMEZONE = "-0700"  # Adjust if needed, e.g. "+0100" for UK BST, "-0700" for Phoenix

# ---- FUNCTIONS ----

def clean_channel_name(name: str) -> str:
    """Normalize channel name for XMLTV id (no spaces, lowercase)."""
    return name.strip().lower().replace(" ", "_").replace("/", "_")

def build_programme(channel_id, event, time_str, day_str):
    """Construct a programme entry for XMLTV."""
    # Attempt to parse date and time
    # Example: "Saturday 18th Oct2025 - Schedule Time UK GMT"
    try:
        # Extract the date from the day string
        date_part = " ".join(day_str.split()[:3])  # "Saturday 18th Oct2025"
        date_obj = datetime.strptime(date_part.replace("th", "").replace("st", "").replace("nd", "").replace("rd", ""), "%A %d %b%Y")
    except Exception:
        date_obj = datetime.utcnow()

    # Parse HH:MM
    try:
        hour, minute = map(int, time_str.split(":"))
    except Exception:
        hour, minute = (0, 0)

    start_time = date_obj.replace(hour=hour, minute=minute)
    end_time = start_time + timedelta(hours=1)  # default duration = 1h

    start_str = start_time.strftime("%Y%m%d%H%M%S") + " " + TIMEZONE
    end_str = end_time.strftime("%Y%m%d%H%M%S") + " " + TIMEZONE

    programme = ET.Element("programme", start=start_str, stop=end_str, channel=channel_id)

    title = ET.SubElement(programme, "title", lang="en")
    title.text = event

    desc = ET.SubElement(programme, "desc", lang="en")
    desc.text = f"{event} on {channel_id}"

    return programme

# ---- MAIN ----

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    tv = ET.Element("tv")

    channels_seen = set()

    for day, categories in data.items():
        for category, events in categories.items():
            for event_item in events:
                event_name = event_item.get("event")
                time_str = event_item.get("time", "00:00")

                for ch in event_item.get("channels", []):
                    ch_name = ch.get("channel_name")
                    ch_id = clean_channel_name(ch_name)

                    if ch_id not in channels_seen:
                        # Add a <channel> entry once per channel
                        channel_el = ET.Element("channel", id=ch_id)
                        display_name = ET.SubElement(channel_el, "display-name")
                        display_name.text = ch_name
                        tv.append(channel_el)
                        channels_seen.add(ch_id)

                    # Add the <programme> entry
                    programme_el = build_programme(ch_id, event_name, time_str, day)
                    tv.append(programme_el)

    tree = ET.ElementTree(tv)
    tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)

    print(f"✅ EPG file generated successfully: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()