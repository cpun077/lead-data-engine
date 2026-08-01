import json
import glob
import sys


output = sys.argv[1]

results = []
seen = set()

for f in glob.glob("/tmp/scrape_*.json"):
    with open(f) as infile:
        for item in json.load(infile):
            if item["url"] not in seen:
                seen.add(item["url"])
                results.append(item)

with open(output, "w") as f:
    json.dump(results, f, indent=2)

print(f"{len(results)} unique results")