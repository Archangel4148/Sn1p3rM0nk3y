import asyncio
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# --- Config ---
BASE_URL = "https://www.bloonswiki.com"
TOWER_LIST_URL = f"{BASE_URL}/Tower"
OUTPUT_DIR = Path("../data/scraped_bloons")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SAVE_HTML = False  # Saves HTML locally
CRAWL_DELAY = 5
TOWERS_TO_PROCESS = 50

def clean_stat(value, is_numeric=False, is_damage_type=False, default=None):
    """Clean a stat value according to the rules."""
    if not value:
        return default

    # Use only the upgraded value after the arrow if present
    if "→" in value:
        value = value.split("→")[-1].strip()
    if "∞" in value:
        value = "1000000"

    # Simplify Damage Type
    if is_damage_type:
        return value.split()[0].strip()

    # Convert numeric values
    if is_numeric:
        # Remove units and non-numeric characters (except . and -)
        value_clean = re.sub(r"[^\d.+-]", "", value)
        try:
            if "." in value_clean:
                return float(value_clean)
            else:
                return int(value_clean)
        except ValueError:
            return value  # fallback to original if conversion fails

    return value.strip()


async def get_html(page, url: str) -> str:
    """Load a page and return its HTML."""
    print(f"[+] Visiting {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await asyncio.sleep(1)
    html = await page.content()
    if SAVE_HTML:
        filename = OUTPUT_DIR / (url.split("/")[-1] + ".html")
        filename.write_text(html, encoding="utf-8")
    return html


def parse_tower_links(html: str):
    """Parse tower links from the /Tower page across all categories."""
    soup = BeautifulSoup(html, "html.parser")
    header = soup.find("span", {"id": "Bloons_TD_6"})
    towers = {}

    if not header:
        print("[-] Could not find Bloons TD 6 section.")
        return towers

    # Loop through all <ul class="gallery mw-gallery-traditional"> after the header
    for gallery in header.find_all_next("ul", class_="gallery mw-gallery-traditional"):
        for a in gallery.find_all("a", href=True, title=True):
            if "(BTD6)" not in a["title"]:
                continue
            title = a["title"].replace(" (BTD6)", "")
            link = BASE_URL + a["href"]
            towers[title] = link

    # Limit to the first N towers if desired
    trim_towers = {key: towers[key] for key in list(towers.keys())[:TOWERS_TO_PROCESS]}
    print(f"[+] Found {len(trim_towers)} towers")
    return trim_towers


def parse_stats_table(html: str):
    """Extract base attack stats from a tower or upgrade page (first Attack table only)."""
    soup = BeautifulSoup(html, "html.parser")
    stats = {
        "Cooldown": None,
        "Range": None,
        "Pierce": None,
        "Damage": None,
        "Damage Type": None,
        "Projectiles": 1,
    }

    # Step 1: Find the "Stats" section
    stats_h2 = soup.find("span", {"id": "Stats"})
    if not stats_h2:
        return stats

    # Step 2: Locate the first Attack table after Stats
    for table in stats_h2.parent.find_all_next("table", class_="stats", limit=10):
        head = table.find("th", class_="head")
        if head and "Attack" in head.text:
            # Found the first Attack table
            for subtable in table.select("table.stats-sub"):
                for row in subtable.find_all("tr"):
                    th = row.find("th")
                    td = row.find("td")
                    if not th or not td:
                        continue

                    key = th.get_text(strip=True).casefold()
                    val = td.get_text(" ", strip=True)

                    if "cooldown" in key:
                        stats["Cooldown"] = clean_stat(val, is_numeric=True)
                    elif "range" in key:
                        stats["Range"] = clean_stat(val, is_numeric=True)
                    elif "pierce" in key:
                        stats["Pierce"] = clean_stat(val, is_numeric=True)
                    elif "damage" == key:
                        stats["Damage"] = clean_stat(val, is_numeric=True, default=0)
                    elif "damage type" in key:
                        stats["Damage Type"] = clean_stat(val, is_damage_type=True)
                    elif "count" in key or "projectiles" in key:
                        stats["Projectiles"] = clean_stat(val, is_numeric=True)
            break  # Only parse the first Attack table

    return stats


def parse_upgrade_links(html: str):
    """Extract upgrade links from the 'Upgrades' section of a tower page."""
    soup = BeautifulSoup(html, "html.parser")
    upgrades = {}

    upgrades_header = soup.find("span", {"id": "Upgrades"})
    if not upgrades_header:
        return upgrades

    h2 = upgrades_header.parent
    for elem in h2.find_all_next():
        if elem.name == "h2" or len(upgrades) == 15:
            break
        if elem.name == "table" and "wide-sub" in elem.get("class", []):
            th = elem.find("th", colspan="2")
            if th:
                a = th.find("a", href=True, title=True)
                if a:
                    href = a["href"]
                    if href.startswith("/"):
                        href = BASE_URL + href
                    title = a["title"].replace(" (BTD6)", "")
                    upgrades[title] = href

    return upgrades


async def main():
    # Load previously saved stats if they exist
    tower_file = OUTPUT_DIR / "tower_stats.json"
    upgrade_file = OUTPUT_DIR / "upgrade_stats.json"

    if tower_file.exists():
        tower_stats = json.loads(tower_file.read_text(encoding="utf-8"))
    else:
        tower_stats = {}

    if upgrade_file.exists():
        upgrade_stats = json.loads(upgrade_file.read_text(encoding="utf-8"))
    else:
        upgrade_stats = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )

        # Step 1: Get tower links
        html = await get_html(page, TOWER_LIST_URL)
        tower_links = parse_tower_links(html)

        # Step 2: Iterate towers
        for tower_name, tower_url in tower_links.items():
            if tower_name in tower_stats:
                print(f"[i] Skipping already processed tower: {tower_name}")
                continue

            print(f"\n=== {tower_name} ===")
            html = await get_html(page, tower_url)
            tower_stats[tower_name] = parse_stats_table(html)

            # Step 3: Parse upgrades
            upgrades = parse_upgrade_links(html)
            upgrade_stats[tower_name] = {}

            for upg_name, upg_url in upgrades.items():
                if upg_name in upgrade_stats.get(tower_name, {}):
                    print(f"  [i] Skipping already processed upgrade: {upg_name}")
                    continue

                print(f"  -> {upg_name}")
                try:
                    html = await get_html(page, upg_url)
                    upgrade_stats[tower_name][upg_name] = parse_stats_table(html)
                except Exception as e:
                    print(f"    [!] Failed: {e}")

                await asyncio.sleep(CRAWL_DELAY)

            await asyncio.sleep(CRAWL_DELAY)

        # Step 4: Save JSON
        tower_file.write_text(json.dumps(tower_stats, indent=2), encoding="utf-8")
        upgrade_file.write_text(json.dumps(upgrade_stats, indent=2), encoding="utf-8")

        await browser.close()

    print("\n✅ Done. Data saved in", OUTPUT_DIR)



if __name__ == "__main__":
    asyncio.run(main())
