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