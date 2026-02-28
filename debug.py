import json
import urllib.parse
import urllib.request
import urllib.error

ODS_KEY = "e09f4f638f"  # if you have one
BASE = "https://data.stib-mivb.brussels/api/explore/v2.1/catalog/datasets/waiting-time-rt-production/records"

params = {"limit": 1}
url = BASE + "?" + urllib.parse.urlencode(params)

headers = {
    "Accept": "application/json",
    "User-Agent": "key-test/1.0",
}

# Opendatasoft Explore API key (if you have it)
if ODS_KEY:
    headers["Authorization"] = f"Apikey {ODS_KEY}"

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("HTTP:", resp.status)
        print("X-RateLimit-Limit:", resp.headers.get("X-RateLimit-Limit"))
        print("X-RateLimit-Remaining:", resp.headers.get("X-RateLimit-Remaining"))
        print("X-RateLimit-Reset:", resp.headers.get("X-RateLimit-Reset"))
        data = json.loads(resp.read().decode("utf-8", "ignore"))
        print("keys:", list(data.keys()))
        print("results_len:", len(data.get("results", [])))
except urllib.error.HTTPError as e:
    body = e.read(500).decode("utf-8", "ignore")
    print("HTTPError:", e.code, body)
    
####

import json
import urllib.parse
import urllib.request
import urllib.error

APIM_KEY = ""  # bmc-partner-key
BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes/"

params = {"limit": 1}
url = BASE + "?" + urllib.parse.urlencode(params)

headers = {
    "Accept": "application/json",
    "User-Agent": "key-test/1.0",
    "bmc-partner-key": APIM_KEY,
}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        ctype = (resp.headers.get("Content-Type") or "")
        text = resp.read().decode("utf-8", "ignore")
        print("HTTP:", resp.status)
        print("Content-Type:", ctype)
        print("Body head:", text[:200])
        if "json" in ctype.lower():
            data = json.loads(text)
            print("keys:", list(data.keys()))
            print("records_len:", len(data.get("records", [])))
except urllib.error.HTTPError as e:
    body = e.read(500).decode("utf-8", "ignore")
    print("HTTPError:", e.code, body[:200])
    
#####

import urllib.parse
import urllib.request
import urllib.error

APIM_KEY = "d3"
BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes/"

url = BASE + "?" + urllib.parse.urlencode({"limit": 1})

headers = {
    "bmc-partner-key": APIM_KEY.strip(),
    "Accept": "application/json",
    "User-Agent": "key-test/1.0",
}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "ignore")
        print("HTTP:", resp.status)
        print("Content-Type:", resp.headers.get("Content-Type"))
        print("x-request-id:", resp.headers.get("x-request-id"))
        print("Body head:", body[:300])
except urllib.error.HTTPError as e:
    body = e.read(800).decode("utf-8", "ignore")
    print("HTTPError:", e.code)
    print("Content-Type:", e.headers.get("Content-Type"))
    print("Body head:", body[:300])
    
    
####

from urllib.parse import urlencode, quote
import requests

BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes"  # <-- no trailing slash

where = 'pointid="6803" or pointid="1674" or pointid="2506" or pointid="1014"'
where = 'pointid LIKE "%6803%"'


where = 'pointid="6803" OR pointid="1674" OR pointid="2506" OR pointid="1014"'
where = 'pointid LIKE "%6803%" OR pointid LIKE "%1674%" OR pointid LIKE "%2506%" OR pointid LIKE "%1014%"'
where = 'pointid IN ("6803","1674","2506","1014")'
where = "pointid=6803 OR pointid=1674 OR pointid=2506 OR pointid=1014"
where = 'pointid:"6803" OR pointid:"1674"'
where = 'pointid = "6803" OR pointid = "1674"'
where = "pointid = 6803 OR pointid = 1674" 

params = {"limit": 100, "where": where}
params = {"$filter": "pointid eq 6803 or pointid eq 1674", "limit": 100}
params = {"$where": "pointid IN('6803','1674')", "$limit": 100}


where = "pointid='6803' OR pointid='1674' OR pointid='2506' OR pointid='1014'"
params = {"limit": 100, "where": where}

# OPTION A: subscription key header (most common in Azure APIM)
headers = {"Ocp-Apim-Subscription-Key": "d3"}  # sometimes it's "subscription-key" instead

r = requests.get(BASE, params=params, headers=headers, timeout=20)
print("URL:", r.url)
print("STATUS:", r.status_code)
print("BODY:", r.text[:500])

BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes"
r = requests.get(BASE, params={"limit": 1}, timeout=20)
print(r.status_code)
print(r.json())

params = {"limit": 100, "refine": "pointid:6803"}

r = requests.get(BASE, params=params, headers=headers, timeout=20)
data = r.json()

# Step 2: print a full record
import json
print(json.dumps(data, indent=2))


import requests
import json

BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes"
headers = {"Ocp-Apim-Subscription-Key": "d3"}

# Try each candidate and print filtered_count to see which one "sticks"
candidates = [
    {"where": "pointid='6803'"},
    {"where": 'pointid="6803"'},
    {"where": "pointid=6803"},
    {"filter": "pointid='6803'"},
    {"filter": "pointid=6803"},
    {"$filter": "pointid eq '6803'"},
    {"$filter": "pointid eq 6803"},
    {"pointid": "6803"},           # maybe field name is a direct param
    {"q": "6803"},
    {"search": "6803"},
]

for params in candidates:
    params["limit"] = 5
    r = requests.get(BASE, params=params, headers=headers, timeout=20)
    data = r.json()
    filtered = data.get("metadata", {}).get("filtered_count", "?")
    print(f"{list(params.items())[0]} → filtered_count={filtered}  status={r.status_code}")
    
    
from urllib.parse import urlencode
import requests

BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes"
headers = {"Ocp-Apim-Subscription-Key": "d3"}

where = "pointid='6803' OR pointid='1674' OR pointid='2506' OR pointid='1014'"

# Build query string manually so you can inspect the exact URL
qs = urlencode({"limit": 100, "where": where})
url = f"{BASE}?{qs}"
print("URL:", url)

r = requests.get(url, headers=headers, timeout=20)
data = r.json()
print("filtered_count:", data["metadata"]["filtered_count"])
print("results:", [x["pointid"] for x in data["results"]])