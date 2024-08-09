import csv
import json

# Define the input and output file names
icons_csv_file = "icons.csv"
items_csv_file = "item.csv"
json_file = "itemIconMap.json"

# Initialize a dictionary to map IconFileDataID to a list of item IDs
icon_to_item_ids_map = {}

# Read the item.csv file and populate the icon_to_item_ids_map
with open(items_csv_file, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        item_id = int(row["ID"])
        icon_file_data_id = int(row["IconFileDataID"])
        if icon_file_data_id not in icon_to_item_ids_map:
            icon_to_item_ids_map[icon_file_data_id] = []
        icon_to_item_ids_map[icon_file_data_id].append(item_id)

# Initialize a dictionary to hold the final item icon mapping
item_icon_map = {}

# Read the icons.csv file and map to the list of item IDs using icon_to_item_ids_map
with open(icons_csv_file, "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        icon_file_data_id = int(row["ID"])
        icon_path = row["path"]

        # Find the corresponding list of item IDs
        if icon_file_data_id in icon_to_item_ids_map:
            item_ids = icon_to_item_ids_map[icon_file_data_id]
            item_icon_map[icon_path] = item_ids

# Write the dictionary to a JSON file
with open(json_file, "w") as f:
    json.dump(item_icon_map, f, indent=4)

print(f"Item icon mapping has been exported to {json_file}")
