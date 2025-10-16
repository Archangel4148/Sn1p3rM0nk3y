import json
import requests
from bs4 import BeautifulSoup

def parse_btd6_upgrades_first_table(url, output_file="btd6_upgrades.json"):
    response = requests.get(url)
    response.raise_for_status()
    html = response.text

    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", {"class": "mw-parser-output"})
    if not content:
        raise ValueError("Could not find main content div")

    # Find the first table only
    table = content.find("table")
    if not table:
        raise ValueError("No table found on page")

    data = {}
    current_tower = None
    current_path = None

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue

        n = len(tds)
        if n == 7:
            upgrade_col, tower_col, path_col, tier_col, cost_col = 1, 2, 3, 4, 5
        elif n == 6:
            upgrade_col, path_col, tier_col, cost_col = 1, 2, 3, 4
        elif n == 5:
            upgrade_col, tier_col, cost_col = 1, 2, 3
            path_col = None
        else:
            continue

        if n == 7:
            current_tower = tds[tower_col].get_text(strip=True)
            if current_tower not in data:
                data[current_tower] = []

        if path_col is not None and path_col < len(tds):
            current_path = tds[path_col].get_text(strip=True)
        path = int(current_path) if current_path else None

        tier = int(tds[tier_col].get_text(strip=True))

        name_tag = tds[upgrade_col].find("b")
        name = name_tag.get_text(strip=True) if name_tag else None

        effect = ""
        if name_tag:
            effect_parts = []
            sibling = name_tag.next_sibling
            while sibling:
                if isinstance(sibling, str):
                    effect_parts.append(sibling.strip())
                elif getattr(sibling, "get_text", None):
                    effect_parts.append(sibling.get_text(strip=True))
                sibling = sibling.next_sibling
            effect = " ".join(part for part in effect_parts if part)

        cost = None
        for td in tds:
            text = td.get_text(strip=True)
            if text.startswith("$"):
                cost = int(text[1:].replace(",", "").replace("*", ""))
                break

        if current_tower and name and effect and cost is not None:
            if current_tower not in data:
                data[current_tower] = []

            data[current_tower].append({
                "path": path,
                "tier": tier,
                "name": name,
                "effect": effect,
                "cost": cost
            })

    # Save JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Processed first table and saved to {output_file}")
    return data


if __name__ == "__main__":
    url = "https://www.bloonswiki.com/List_of_upgrades_in_BTD6"
    parse_btd6_upgrades_first_table(url)
