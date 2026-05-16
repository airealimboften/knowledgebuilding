# -*- coding: utf-8 -*-
import urllib.request, json
url = "https://api.github.com/repos/airealimboften/knowledgebuilding/discussions/categories"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read().decode("utf-8"))
for cat in data:
    print(cat["name"], " | node_id:", cat.get("node_id", "N/A"))
