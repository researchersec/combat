import json
import csv
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Load combatant names from JSON file
with open("combatantNames.json", "r", encoding="utf-8") as f:
    combatant_names = json.load(f)

# Load item enchant resistances from JSON file
with open("itemEnchantResistances.json", "r", encoding="utf-8") as f:
    item_enchant_resistances = json.load(f)

# Load item data from CSV file, including resistance
item_data = {}
with open("itemsparse.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            item_id = int(row["ID"])
            item_data[item_id] = {
                "item_name": row["Display_lang"],
                "item_level": int(row["ItemLevel"]) if row["ItemLevel"] else 0,
                "item_quality": row["OverallQualityID"],
                "base_resistance": (
                    int(row["Resistances[2]"]) if row["Resistances[2]"] else 0
                ),
            }
        except ValueError as e:
            logging.warning(f"Skipping item with invalid data: {e}")


def calculate_total_resistance(base_resistance, bonuses):
    total_resistance = base_resistance
    for bonus in bonuses:
        resistance_bonus = item_enchant_resistances.get(str(bonus), 0)
        total_resistance += resistance_bonus
    return total_resistance


def parse_gear_info(gear_info_str):
    """
    Parses the gear info string and returns a list of gear items with their details.
    """
    gear_items = []
    try:
        # Remove surrounding brackets and whitespace
        gear_info_str = gear_info_str.strip().lstrip("[").rstrip("]").strip()

        # Split the gear info into individual items
        # This regex splits on '), (' boundaries
        item_strings = re.findall(r"\(.*?\)", gear_info_str)

        for item_str in item_strings:
            # Example item_str: (16818,200,()), (16918,200,(123,456))
            # Remove parentheses
            item_str = item_str.strip().lstrip("(").rstrip(")")
            # Split by commas, but account for nested parentheses
            # Split only on commas that are not within parentheses
            parts = []
            nested = 0
            current_part = ""
            for char in item_str:
                if char == "," and nested == 0:
                    parts.append(current_part)
                    current_part = ""
                else:
                    if char == "(":
                        nested += 1
                    elif char == ")":
                        nested -= 1
                    current_part += char
            parts.append(current_part)  # Add the last part

            if len(parts) != 3:
                logging.warning(f"Unexpected item format: {item_str}")
                continue

            item_id_str, item_level_str, bonuses_str = parts
            item_id = int(item_id_str.strip())
            item_level = int(item_level_str.strip())
            bonuses = []

            # Parse bonuses
            bonuses_str = bonuses_str.strip()
            if bonuses_str.startswith("(") and bonuses_str.endswith(")"):
                bonuses_content = bonuses_str[1:-1].strip()
                if bonuses_content:
                    # Split bonuses by comma
                    bonuses = [
                        int(b.strip()) for b in bonuses_content.split(",") if b.strip()
                    ]

            gear_items.append(
                {"item_id": item_id, "item_level": item_level, "bonuses": bonuses}
            )

    except Exception as e:
        logging.error(f"Error parsing gear info: {e}")

    return gear_items


def extract_combatant_info(log_lines):
    combatant_data = {}
    encounter_data = {}
    current_encounter = None

    # Regex to match COMBATANT_INFO lines
    combatant_pattern = re.compile(
        r"COMBATANT_INFO,(Player-\d+-\w+),.*?(\[\(.*?\)\]),.*"
    )
    encounter_start_pattern = re.compile(
        r"ENCOUNTER_START,(\d+),\"([^\"]+)\",(\d+),(\d+),(\d+)"
    )
    encounter_end_pattern = re.compile(
        r"ENCOUNTER_END,(\d+),\"([^\"]+)\",(\d+),(\d+),(\d+)"
    )

    for line in log_lines:
        # Check for encounter start
        encounter_start_match = encounter_start_pattern.match(line)
        if encounter_start_match:
            encounter_id = encounter_start_match.group(1)
            encounter_name = encounter_start_match.group(2)
            current_encounter = encounter_id
            encounter_data[current_encounter] = {
                "name": encounter_name,
                "total_resistance": 0,
                "players": [],
            }

        # Check for encounter end
        encounter_end_match = encounter_end_pattern.match(line)
        if encounter_end_match:
            current_encounter = None

        # Process combatant info lines
        combatant_match = combatant_pattern.search(line)
        if combatant_match:
            player_id = combatant_match.group(1)
            gear_info = combatant_match.group(2)

            # Get the player's name from combatant_names.json
            player_name = combatant_names.get(player_id, player_id)

            # Parse gear info
            gear_items = re.findall(r"\((\d+),(\d+),\((.*?)\)\)", gear_info)
            parsed_gear = []
            total_resistance = 0  # Initialize total resistance for this player
            for item in gear_items:
                item_id, item_level, bonuses = item

                # Skip the item if item_id is 0
                if int(item_id) == 0:
                    continue

                bonuses = bonuses.split(",") if bonuses else []
                bonuses = [
                    int(bonus.strip()) for bonus in bonuses if bonus.strip().isdigit()
                ]

                # Get item details from item_data
                item_details = item_data.get(int(item_id), {})
                item_name = item_details.get("item_name", "Unknown")
                item_quality = item_details.get("item_quality", "Unknown")
                base_resistance = item_details.get("base_resistance", 0)

                # Calculate total resistance for the item
                item_total_resistance = calculate_total_resistance(
                    base_resistance, bonuses
                )
                total_resistance += (
                    item_total_resistance  # Add to player's total resistance
                )

                parsed_gear.append(
                    {
                        "item_id": int(item_id),
                        "item_level": int(item_level),
                        "bonuses": bonuses,
                        "item_name": item_name,
                        "item_quality": item_quality,
                        "total_resistance": item_total_resistance,
                    }
                )

            combatant_data[player_name] = {
                "gear": parsed_gear,
                "total_resistance": total_resistance,  # Store total resistance for this player
            }

            # If we're in an encounter, add this player's resistance to the encounter total
            if current_encounter:
                encounter_data[current_encounter][
                    "total_resistance"
                ] += total_resistance
                encounter_data[current_encounter]["players"].append(player_name)

    return combatant_data, encounter_data


# Load log lines from WoWCombatLog.txt
log_file_path = "WoWCombatLog2.txt"
try:
    with open(log_file_path, "r", encoding="utf-8") as f:
        log_lines = f.readlines()
except FileNotFoundError:
    logging.error(f"Log file not found: {log_file_path}")
    log_lines = []

# Extract combatant gear information and encounter data
combatant_data, encounter_data = extract_combatant_info(log_lines)

# Export combatant data to JSON
combatant_output_file = "combatant_data.json"
with open(combatant_output_file, "w", encoding="utf-8") as f:
    json.dump(combatant_data, f, indent=4, ensure_ascii=False)
    logging.info(f"Combatant data exported to {combatant_output_file}")

# Export encounter data to JSON
encounter_output_file = "encounter_data.json"
with open(encounter_output_file, "w", encoding="utf-8") as f:
    json.dump(encounter_data, f, indent=4, ensure_ascii=False)
    logging.info(f"Encounter data exported to {encounter_output_file}")
