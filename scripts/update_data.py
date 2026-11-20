import json
import os
import urllib.request
from pathlib import Path

API_URL = (
    "https://environment.data.gov.uk/doc/bathing-water.json"
    "?_view=bathing-water&_pageSize=1000&_page=0"
)
OUTPUT_PATH = Path("data/bathing_waters.json")


def _extract_value(field):
    """Handles strings, dicts with '_value', or lists of values from EA JSON."""
    if field is None:
        return None
    if isinstance(field, dict):
        return field.get("_value") or field.get("label") or field.get("_about")
    if isinstance(field, list) and field:
        return _extract_value(field[0])
    return field


def fetch_bathing_waters(url: str = API_URL) -> list[dict]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "UK-Bathing-Water-PWA/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    items = payload.get("result", {}).get("items", [])
    records = []

    for item in items:
        sampling_point = item.get("samplingPoint", {})
        if isinstance(sampling_point, list):
            sampling_point = sampling_point[0] if sampling_point else {}

        name = _extract_value(item.get("name"))
        lat = _extract_value(sampling_point.get("lat"))
        lon = _extract_value(sampling_point.get("long"))
        classification = _extract_value(item.get("latestComplianceAssessment"))
        district = _extract_value(item.get("district"))
        water_company = _extract_value(item.get("waterCompany"))
        bw_id = _extract_value(item.get("eubwidNotation")) or _extract_value(
            item.get("_about")
        )

        # Ensure numeric coordinates when present
        try:
            lat = float(lat) if lat is not None else None
        except (TypeError, ValueError):
            lat = None

        try:
            lon = float(lon) if lon is not None else None
        except (TypeError, ValueError):
            lon = None

        records.append(
            {
                "id": bw_id,
                "name": name,
                "district": district,
                "waterCompany": water_company,
                "classification": classification,
                "lat": lat,
                "lon": lon,
            }
        )

    # Sort deterministically by name so diffs stay clean across runs
    records.sort(key=lambda r: (r["name"] or "").lower())
    return records


def save_if_changed(records: list[dict], output_path: Path = OUTPUT_PATH) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_content = json.dumps(records, indent=2, ensure_ascii=False) + "\n"

    if output_path.exists():
        old_content = output_path.read_text(encoding="utf-8")
        if old_content == new_content:
            print("No changes to bathing water data.")
            return False

    output_path.write_text(new_content, encoding="utf-8")
    print(f"Wrote {len(records)} bathing water records to {output_path}.")
    return True


def main() -> None:
    records = fetch_bathing_waters()
    if not records:
        raise RuntimeError("API returned 0 bathing water records; aborting save.")
    save_if_changed(records)


if __name__ == "__main__":
    main()
