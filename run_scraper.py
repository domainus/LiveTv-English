import requests
import re
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "Referer": "https://daddylive.sx/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        if res.status_code == 200:
            return res.text
    except Exception:
        pass
    return None

def main():
    raw_channels = []
    final_channels = []
    
    print("Scraping 24/7 channels...")
    html_247 = get_html("https://daddylive.sx/24-7-channels.php")
    if html_247:
        soup = BeautifulSoup(html_247, 'html.parser')
        links = soup.find_all('a', href=re.compile(r'id='))
        
        for link in links:
            name = link.text.strip()
            href = link.get('href', '')
            if not name or 'id=' not in href: continue
            ch_id = href.split('id=')[1].split('&')[0]
            
            if name == "Sky Calcio 7 (257) Italy": name = "DAZN"
            if ch_id == "853": name = "Canale 5 Italy"
            
            raw_channels.append((name, ch_id))

    print("Generating proxy URLs...")
    for name, ch_id in raw_channels:
        for play_num in range(1, 7):
            stream_url = f"http://pizzotv.duckdns.org:8080/dlhd/stream-{ch_id}.php?p={play_num}"
            final_channels.append((f"{name} (P{play_num})", stream_url))

    print("Writing formatted IPTV lines...")
    with open("dlhd.m3u", "w", encoding="utf-8", newline='\r\n') as f:
        f.write("#EXTM3U\n\n")
        valid_idx = 1
        for name, url in final_channels:
            clean_name = str(name).split('\n')[0].strip()
            name_lower = clean_name.lower()
            
            if "adult swim" in name_lower:
                pass 
            else:
                adult_keywords = ["xxx", "porn", "adult", "18+", "playboy", "hustler", "penthouse", "pink", "brazzers"]
                if any(word in name_lower for word in adult_keywords):
                    continue
                
            foreign_countries = [
                "italy", "italia", "spain", "espana", "germany", "deutschland", 
                "france", "portugal", "arabic", "netherlands", "greece", "cyprus", 
                "albania", "romania", "poland", "polska", "turkey", "turkiye", 
                "india", "pakistan", "latino", "mexico", "argentina"
            ]
            if any(f" {country}" in name_lower or f"({country})" in name_lower for country in foreign_countries):
                continue
            
            if "live event:" in name_lower or "vs" in name_lower:
                group = "DLHD Live Sports"
            elif "uk" in name_lower:
                group = "DLHD United Kingdom"
            else:
                group = "DLHD United States & General"
                
            f.write(f'#EXTINF:-1 tvg-id="ch-{valid_idx}" tvg-name="{clean_name}" group-title="{group}",{clean_name}\n')
            f.write(f'{url}\n\n')
            valid_idx += 1

if __name__ == "__main__":
    main()
