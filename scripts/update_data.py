import json
import time
import urllib.error
import urllib.request
from pathlib import Path

API_URL = (
    "https://environment.data.gov.uk/doc/bathing-water.json"
    "?_view=bathing-water&_pageSize=500&_page=0"
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


def _fetch_json_with_retry(url: str, max_attempts: int = 5, base_delay: float = 5.0) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "UK-Bathing-Water-PWA/1.0 (+https://github.com/harrycarmel68/uk-bathing-water-pwa)",
        },
    )

    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            retryable = exc.code in (429, 500, 502, 503, 504)
            if not retryable or attempt == max_attempts:
                raise
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after and retry_after.isdigit():
                sleep_for = max(float(retry_after), base_delay)
            else:
                sleep_for = base_delay * (2 ** (attempt - 1))
            print(
                f"HTTP {exc.code} from EA API (attempt {attempt}/{max_attempts}). "
                f"Waiting {sleep_for:.1f}s before retrying..."
            )
            time.sleep(sleep_for)
        except urllib.error.URLError as exc:
            if attempt == max_attempts:
                raise
            sleep_for = base_delay * (2 ** (attempt - 1))
            print(
                f"Network error ({exc.reason}) on attempt {attempt}/{max_attempts}. "
                f"Waiting {sleep_for:.1f}s before retrying..."
            )
            time.sleep(sleep_for)

    raise RuntimeError("Exhausted retry attempts.")


def fetch_bathing_waters(url: str = API_URL) -> list[dict]:
    payload = _fetch_json_with_retry(url)
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
