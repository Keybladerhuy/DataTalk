"""Convert pokedex.ts to a flat CSV file using regex field extraction."""

import csv
import re
from pathlib import Path

HERE = Path(__file__).parent
TS_FILE = HERE / "pokedex.ts"
CSV_FILE = HERE / "pokedex.csv"


def extract_entries(text: str) -> list[tuple[str, str]]:
    """Extract top-level entries as (key, block_text) pairs."""
    # Match top-level keys: a word at one-tab indent followed by a block
    pattern = re.compile(r'^\t(\w+):\s*\{(.*?)\n\t\}', re.MULTILINE | re.DOTALL)
    return pattern.findall(text)


def extract_field(block: str, field: str) -> str:
    """Extract a simple scalar field value."""
    m = re.search(rf'{field}:\s*"([^"]*)"', block)
    if m:
        return m.group(1)
    m = re.search(rf'{field}:\s*([\d.]+)', block)
    if m:
        return m.group(1)
    return ""


def extract_array(block: str, field: str) -> list[str]:
    """Extract a string array field."""
    m = re.search(rf'{field}:\s*\[([^\]]*)\]', block)
    if not m:
        return []
    return re.findall(r'"([^"]*)"', m.group(1))


def extract_base_stats(block: str) -> dict:
    """Extract baseStats object."""
    m = re.search(r'baseStats:\s*\{([^}]*)\}', block)
    if not m:
        return {}
    stats = {}
    for key, val in re.findall(r'(\w+):\s*(\d+)', m.group(1)):
        stats[key] = val
    return stats


def extract_abilities(block: str) -> dict:
    """Extract abilities object."""
    m = re.search(r'abilities:\s*\{([^}]*)\}', block)
    if not m:
        return {}
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', m.group(1)))


def extract_gender_ratio(block: str) -> dict:
    """Extract genderRatio object."""
    m = re.search(r'genderRatio:\s*\{([^}]*)\}', block)
    if not m:
        return {}
    return dict(re.findall(r'(\w+):\s*([\d.]+)', m.group(1)))


def flatten(key: str, block: str) -> dict:
    """Flatten a single Pokemon entry block into a CSV row."""
    types = extract_array(block, "types")
    stats = extract_base_stats(block)
    abilities = extract_abilities(block)
    gender = extract_gender_ratio(block)
    egg_groups = extract_array(block, "eggGroups")

    return {
        "id": key,
        "num": extract_field(block, "num"),
        "name": extract_field(block, "name"),
        "type1": types[0] if len(types) > 0 else "",
        "type2": types[1] if len(types) > 1 else "",
        "hp": stats.get("hp", ""),
        "atk": stats.get("atk", ""),
        "def": stats.get("def", ""),
        "spa": stats.get("spa", ""),
        "spd": stats.get("spd", ""),
        "spe": stats.get("spe", ""),
        "ability_primary": abilities.get("0", ""),
        "ability_secondary": abilities.get("1", ""),
        "ability_hidden": abilities.get("H", ""),
        "height_m": extract_field(block, "heightm"),
        "weight_kg": extract_field(block, "weightkg"),
        "color": extract_field(block, "color"),
        "egg_groups": "; ".join(egg_groups),
        "gender_ratio_m": gender.get("M", ""),
        "gender_ratio_f": gender.get("F", ""),
        "forme": extract_field(block, "forme"),
        "base_species": extract_field(block, "baseSpecies"),
    }


COLUMNS = [
    "id", "num", "name", "type1", "type2",
    "hp", "atk", "def", "spa", "spd", "spe",
    "ability_primary", "ability_secondary", "ability_hidden",
    "height_m", "weight_kg", "color", "egg_groups",
    "gender_ratio_m", "gender_ratio_f", "forme", "base_species",
]


def main():
    text = TS_FILE.read_text(encoding="utf-8")
    entries = extract_entries(text)

    rows = [flatten(key, block) for key, block in entries]

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} Pokemon to {CSV_FILE}")


if __name__ == "__main__":
    main()
