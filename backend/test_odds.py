import os
import requests

API_IO_KEY = os.getenv("ODDS_API_IO_KEY", "")

def test():
    url = "https://api.odds-api.io/v3/events"
    params = {"apiKey": API_IO_KEY, "sport": "ice-hockey", "status": "pending"}
    r = requests.get(url, params=params)
    print("Status:", r.status_code)
    if r.status_code == 200:
        events = r.json()
        print(f"Total: {len(events)}")
        found_slugs = set()
        for e in events:
            slug = e.get("league", {}).get("slug", "")
            found_slugs.add(slug)
        print("Slugs inside ice-hockey:")
        for s in sorted(list(found_slugs)):
            print("-", s)
    else:
        print("Error:", r.text)

if __name__ == "__main__":
    test()
