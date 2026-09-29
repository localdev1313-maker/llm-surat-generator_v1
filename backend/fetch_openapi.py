import json
import urllib.request

url = "http://127.0.0.1:8001/openapi.json"
try:
    with urllib.request.urlopen(url) as resp:
        data = json.load(resp)
    # Save to file for inspection
    with open("openapi.json", "w") as f:
        json.dump(data, f, indent=2)
    print("SUCCESS: OpenAPI spec fetched and saved to openapi.json")
    # Check for generate-nota-dinas path
    paths = data.get("paths", {})
    if "/generate-nota-dinas" in paths:
        print("✓ /generate-nota-dinas endpoint found in OpenAPI spec")
        method = paths["/generate-nota-dinas"]
        print(f"  Methods: {list(method.keys())}")
    else:
        print("✗ /generate-nota-dinas NOT found in OpenAPI spec")
        # List available paths
        for p in sorted(paths.keys()):
            print(f"  - {p}")
except Exception as e:
    print(f"ERROR fetching OpenAPI spec: {e}")