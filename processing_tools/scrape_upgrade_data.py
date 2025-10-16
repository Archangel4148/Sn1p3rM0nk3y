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
            print(current_tower)
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

def mark_camo_upgrades(json_path, output_path="btd6_upgrades_camo.json"):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    camo_sources = {
        "Dart Monkey": ["0-0-2"],
        "Boomerang Monkey": ["5-0-0", "0-4-0"],
        "Bomb Shooter": ["0-0-5"],
        "Desperado": ["0-1-0"],
        "Ice Monkey": ["2-0-0"],
        "Glue Gunner": ["0-4-0"],
        "Sniper Monkey": ["0-1-0"],
        "Monkey Sub": ["3-0-0"],
        "Monkey Buccaneer": ["0-0-2"],
        "Monkey Ace": ["0-2-0"],
        "Heli Pilot": ["0-2-0"],
        "Mortar Monkey": ["0-0-3", "0-5-0"],
        "Dartling Gunner": ["0-1-0"],
        "Wizard Monkey": ["0-0-2", "0-0-3", "5-0-0"],
        "Super Monkey": ["0-0-2", "0-4-0"],
        "Ninja Monkey": ["0-0-0", "0-2-0"],
        "Druid": ["5-0-0", "0-5-0"],
        "Mermonkey": ["0-0-1"],
        "Spike Factory": ["0-0-0"],
        "Monkey Village": ["0-2-0", "5-0-0"],
        "Engineer Monkey": ["0-3-0"],
        "Beast Handler": ["0-0-2"],
    }

    for tower, upgrades in data.items():
        camo_list = camo_sources.get(tower, [])  # empty if tower not in dict

        for upgrade in upgrades:
            combo = ["0", "0", "0"]
            combo[upgrade["path"] - 1] = str(upgrade["tier"])
            combo_str = "-".join(combo)

            upgrade["grants_camo"] = combo_str in camo_list

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Added camo info to {output_path}")


def mark_lead_upgrades(json_path, output_path="btd6_upgrades_lead.json"):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Upgrades that enable lead popping for each tower
    lead_sources = {
        "Dart Monkey": ["4-0-0", "0-5-0", "0-0-5"],
        "Boomerang Monkey": ["0-0-2"],
        "Glue Monkey": ["2-0-0"],
        "Tack Shooter": ["3-0-0", "0-5-0"],
        "Ice Monkey": ["2-0-0", "0-5-0"],
        "Sniper Monkey": ["1-0-0", "0-4-0"],
        "Monkey Sub": ["0-2-0"],
        "Monkey Buccaneer": ["0-2-0"],
        "Monkey Ace": ["0-1-0", "0-0-4", "5-0-0"],
        "Heli Pilot": ["3-0-0", "0-5-0", "0-0-3"],
        "Dartling Gunner": ["0-3-0", "4-0-0"],
        "Wizard Monkey": ["0-1-0", "0-0-4", "4-0-0"],
        "Super Monkey": ["2-0-0", "0-4-0", "0-0-4"],
        "Ninja Monkey": ["0-0-3"],
        "Druid": ["1-0-0"],
        "Spike Factory": ["2-0-0"],
        "Monkey Village": ["0-3-0", "5-0-0"],
        "Engineer Monkey": ["0-3-0", "4-0-0"],
        "Beast Handler": ["0-2-0", "3-0-0", "0-0-5"],
    }

    for tower, upgrades in data.items():
        for upgrade in upgrades:
            combo = ["0", "0", "0"]
            combo[upgrade["path"] - 1] = str(upgrade["tier"])
            combo_str = "-".join(combo)

            upgrade["grants_lead"] = combo_str in lead_sources.get(tower, [])

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Added lead info to {output_path}")

def mark_upgrade_ranges(json_path, output_path="btd6_upgrades_range.json"):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    range_values = {
        "Ice Monkey": [("0-4-0", 10), ("0-5-0", 10), ("0-0-1", 7), ("0-0-4", 16)],
        "Tack Shooter": [("5-0-0", 12), ("0-1-0", 4), ("0-2-0", 4), ("0-0-5", 7)],
        "Dart Monkey": [("4-0-0", 7), ("0-4-0", 4), ("0-5-0", 4), ("0-0-1", 8), ("0-0-2", 8), ("0-0-3", 8), ("0-0-4", 4), ("0-0-5", 20)],
        "Spike Factory": [("0-0-1", 8)],
        "Druid": [("0-4-0", 10), ("0-0-1", 10), ("0-0-5", 5)],
        "Bomb Shooter": [("4-0-0", 3), ("0-2-0", 4), ("0-3-0", 5), ("0-4-0", 5), ("0-0-1", 7), ("0-0-2", 2)],
        "Wizard Monkey": [("3-0-0", 20), ("0-0-2", 10), ("0-0-3", 10), ("0-0-5", 20)],
        "Ninja Monkey": [("5-0-0", 10), ("0-0-1", 7), ("0-0-4", 8)],
        "Monkey Village": [("1-0-0", 8), ("5-0-0", 8), ("0-0-4", 10)],
        "Engineer Monkey": [("1-0-0", 5), ("3-0-0", 4), ("0-1-0", 20)],
        "Monkey Sub": [("1-0-0", 10), ("0-3-0", 8)],
        "Boomerang Monkey": [("0-0-1", 14)],
        "Alchemist": [("5-0-0", 20), ("0-3-0", 22)],
        "Super Monkey": [("0-1-0", 10), ("0-2-0", 12), ("0-5-0", 10), ("0-0-2", 3), ("0-0-5", 4)],
        "Monkey Buccaneer": [("0-0-1", 11)],
        "Beast Handler": [("1-0-0", 5), ("2-0-0", 5), ("3-0-0", 10), ("4-0-0", 10), ("5-0-0", 10), ("0-3-0", 4), ("0-4-0", 6), ("0-5-0", 20)],
        "Mermonkey": [("0-0-2", 2)],
    }

    # Convert range_values into a quick lookup table
    range_lookup = {}
    for tower, entries in range_values.items():
        range_lookup[tower] = {combo: value for combo, value in entries}

    # Apply range data
    for tower, upgrades in data.items():
        for upgrade in upgrades:
            combo = ["0", "0", "0"]
            combo[upgrade["path"] - 1] = str(upgrade["tier"])
            combo_str = "-".join(combo)

            added_range = range_lookup.get(tower, {}).get(combo_str, 0)
            upgrade["added_range"] = added_range

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"Added range info to {output_path}")


if __name__ == "__main__":
    # url = "https://www.bloonswiki.com/List_of_upgrades_in_BTD6"
    # parse_btd6_upgrades_first_table(url)
    # mark_camo_upgrades(
    #     json_path=r"btd6_upgrades.json",
    #     output_path=r"btd6_upgrades_camo.json"
    # )
    # mark_lead_upgrades("btd6_upgrades_camo.json")
    # mark_upgrade_ranges("btd6_upgrades_lead.json")
    pass