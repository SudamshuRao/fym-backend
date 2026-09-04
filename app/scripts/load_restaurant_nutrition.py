"""
Loads the JSON files produced by scrape_nutrition.py (mcdonalds.json,
chipotle.json, etc.) into the restaurant_nutrition table.

This is the missing link between the scraper pipeline (which writes to
local JSON files) and the app (which reads from Postgres) - run this
once after scraping, and again any time the scraper is re-run with
updated data.

Only loads "ok_structured" records - "ok_raw" records need the LLM
labeling step (label_data.py) first, which hasn't been run for any of
the current restaurants since all 10 resolved via structured parsing.

Usage:
    python3 -m app.scripts.load_restaurant_nutrition /path/to/json/folder

Re-running is safe: existing rows for a restaurant are deleted and
replaced with the freshly loaded data, rather than duplicating rows on
every run.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from app.core.database import SessionLocal
from app.models.restaurant_nutrition import RestaurantNutrition


def slugify(name: str) -> str:
    return name.lower().replace("'", "").replace(" ", "-")


def load_file(db, filepath: Path) -> int:
    with open(filepath) as f:
        record = json.load(f)

    if record.get("status") != "ok_structured":
        print(f"  Skipping {filepath.name}: status is '{record.get('status')}', not 'ok_structured'")
        return 0

    restaurant_name = record["restaurant"]
    restaurant_id = slugify(restaurant_name)
    source_url = record.get("source_url")

    # Replace, don't duplicate: clear any existing rows for this restaurant first.
    deleted = db.query(RestaurantNutrition).filter(
        RestaurantNutrition.restaurant_id == restaurant_id
    ).delete()
    if deleted:
        print(f"  Removed {deleted} existing rows for {restaurant_name}")

    count = 0
    for item in record["menu_items"]:
        row = RestaurantNutrition(
            restaurant_id=restaurant_id,
            name=restaurant_name,
            menu_item=item["menu_item"],
            protein=item.get("protein"),
            carb=item.get("carb"),
            fat=item.get("fat"),
            cal=item.get("cal"),
            attribute_tags=[],  # populated later by the keyword-tagging step
            source_url=source_url,
            last_fetched=datetime.utcnow(),
            status="ok_structured",
        )
        db.add(row)
        count += 1

    return count


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 -m app.scripts.load_restaurant_nutrition /path/to/json/folder")
        sys.exit(1)

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Not a directory: {folder}")
        sys.exit(1)

    json_files = sorted(folder.glob("*.json"))
    json_files = [f for f in json_files if not f.name.startswith("_")]  # skip _manifest.json etc.

    if not json_files:
        print(f"No .json files found in {folder}")
        sys.exit(1)

    db = SessionLocal()
    total = 0
    try:
        for filepath in json_files:
            print(f"Loading {filepath.name} ...")
            count = load_file(db, filepath)
            total += count
            print(f"  -> {count} items")
        db.commit()
        print(f"\nDone. Loaded {total} items total across {len(json_files)} files.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
