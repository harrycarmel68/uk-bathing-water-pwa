import json
import time
import urllib.error
import urllib.request

BASE_URL = "https://environment.data.gov.uk/doc/bathing-water.json"


def test_page_size(page_size: int) -> None:
    url = f"{BASE_URL}?_view=bathing-water&_pageSize={page_size}&_page=0"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "UK-Bathing-Water-PWA-Test/1.0",
        },
    )

    print(f"\n--- Testing _pageSize={page_size} ---")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
            items = payload.get("result", {}).get("items", [])
            print(f"SUCCESS: HTTP {resp.status}, received {len(items)} items, size={len(raw)} bytes")
            for key in ("Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
                if key in resp.headers:
                    print(f"  Header {key}: {resp.headers[key]}")
    except urllib.error.HTTPError as exc:
        print(f"FAILED: HTTP {exc.code} ({exc.reason})")
        if exc.headers:
            for key in ("Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
                if key in exc.headers:
                    print(f"  Header {key}: {exc.headers[key]}")
    except urllib.error.URLError as exc:
        print(f"NETWORK ERROR: {exc.reason}")


def main() -> None:
    for size in (1, 10, 50):
        test_page_size(size)
        time.sleep(3)


if __name__ == "__main__":
    main()
