import streamlit as st
import requests

API_KEY = st.secrets["STIB_API_KEY"]

url = "https://stibmivb.opendatasoft.com/api/explore/v2.1/catalog/datasets/waiting-time-rt-production/records"
params = {"limit": 1}

# 1) No key (this dataset is often public, so this may return 200)
r0 = requests.get(url, params=params, timeout=20)
st.sidebar.write("no key ->", r0.status_code)

# 2) With key in header
headers = {"Authorization": f"Apikey {API_KEY}"}
r1 = requests.get(url, params=params, headers=headers, timeout=20)
st.sidebar.write("header key ->", r1.status_code, r1.text[:200])

# 3) With key as query param
r2 = requests.get(url, params={**params, "apikey": API_KEY}, timeout=20)
st.sidebar.write("param key ->", r2.status_code, r2.text[:200])

# Quick key sanity (don’t print the full key)
st.sidebar.write("key length ->", len(API_KEY))
st.sidebar.write("key preview ->", API_KEY[:4] + "…" + API_KEY[-4:])

##

import requests
import streamlit as st

BMC_KEY = st.secrets["STIB_API_KEY"].strip()

url = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes/ HTTP/1.1"


url = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes/"

params = {
    "limit": 5,          # optional
    # "where": 'pointid="2027" AND lineid="42"',   # example filter
    # "select": "pointid,lineid,passingtimes",
}

headers = {
    "Cache-Control": "no-cache",
    "bmc-partner-key": BMC_KEY,
}

r = requests.get(url, params=params, headers=headers, timeout=20)
st.sidebar.write("status ->", r.status_code)

data = r.json()
st.write("rows ->", len(data.get("results", [])))

# Parse the 'passingtimes' field (string -> list[dict])
rows = data.get("results", [])
if rows:
    pt = json.loads(rows[0]["passingtimes"])
    st.write("first row:", {k: rows[0][k] for k in ("pointid", "lineid")})
    st.write("first row passingtimes (parsed):")
    st.json(pt[:2])