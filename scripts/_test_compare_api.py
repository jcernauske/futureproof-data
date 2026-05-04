"""Quick test of the compare API endpoint."""
import json
import urllib.request

req = urllib.request.Request(
    "http://localhost:8000/builds/compare",
    data=json.dumps({"build_ids": ["indiana-state-university-025", "ball-state-university-024"]}).encode(),
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        top = list(data)
        print("Top-level:", top)
        print(f"Builds: {len(data['builds'])}")
        for b in data["builds"]:
            print(f"  {b['school_name']}: median_wage={b.get('median_annual_wage')}, cost4yr={b.get('published_cost_4yr')}, debt={b.get('modeled_total_debt')}, net_price={b.get('net_price_annual')}")
        print(f"Stats: {len(data['stats'])}")
        for s in data["stats"]:
            print(f"  {s['label']}: {s['values']}")
        print(f"Bosses: {len(data['bosses'])}")
        for bo in data["bosses"]:
            print(f"  {bo['boss_id']}: {bo['values']}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode()}")
