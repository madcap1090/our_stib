import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

BRUSSELS = ZoneInfo("Europe/Brussels")

display = "nl"  # "nl" or "fr"

stations = {
    "fr": {"6803": "LENOIR", "1674": "BRUXELLOIS", "2506": "MIRRIOR", "1014": "MIRRIOR"},
    "nl": {"6803": "LENOIR", "1674": "BRUSSELAARS", "2506": "SPIEGEL", "1014": "SPIEGEL"},
}
stop_ids = list(stations["fr"].keys())

# Cloudflare Worker URL (NOT the STIB/OpenDataSoft URL)
BASE_PROXY = "https://stib-proxy.stib-proxy.madcap1090.workers.dev"
CACHE_TTL_S = 60


def parse_dt(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def build_where_pointid_in(ids: list[str]) -> str:
    return f"pointid in ({', '.join(repr(s) for s in ids)})"


@st.cache_resource
def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "stib-streamlit/1.0"})
    return s


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def fetch_via_proxy(where: str) -> list[dict]:
    # The worker expects where/limit and returns the upstream JSON unchanged
    params = {"limit": 100, "where": where}

    s = get_session()
    r = s.get(BASE_PROXY, params=params, timeout=30)

    # if the worker returns a non-200, show it
    r.raise_for_status()

    payload = r.json() if r.text.strip() else {}
    return payload.get("results", [])


def build_board(records):
    now = datetime.now(BRUSSELS)
    by_stop = {sid: [] for sid in stop_ids}

    for rec in records:
        sid = rec.get("pointid")
        if sid not in by_stop:
            continue

        pts = json.loads(rec.get("passingtimes") or "[]")
        for p in pts:
            line = str(p.get("lineId") or rec.get("lineid") or "").strip()
            dest = (p.get("destination") or {}).get(display, "")
            eta_s = p.get("expectedArrivalTime")
            if not (line and dest and eta_s):
                continue

            eta = parse_dt(eta_s).astimezone(BRUSSELS)
            mins = int((eta - now).total_seconds() // 60)
            by_stop[sid].append((max(0, mins), line, dest))

    out = []
    for sid in stop_ids:
        title = stations[display].get(sid, sid)
        deps = sorted(by_stop[sid], key=lambda t: t[0])[:8]
        out.append((title, deps))
    return out


# ---------------- UI ----------------
st.set_page_config(page_title="STIB LCD", layout="centered")

import ssl
import sys
import requests
import streamlit as st

TEST_URLS = [
    "https://example.com",
    "https://www.google.com",
    "https://api.github.com",
    "https://cloudflare.com",
]

st.sidebar.write("Connectivity tests:")
for u in TEST_URLS:
    try:
        r = requests.get(u, timeout=10)
        st.sidebar.write(u, "->", r.status_code)
    except Exception as e:
        st.sidebar.write(u, "->", repr(e))
st.sidebar.write("Python:", sys.version)
st.sidebar.write("OpenSSL:", ssl.OPENSSL_VERSION)

force_refresh = st.button("↻", help="Refresh")

where = build_where_pointid_in(stop_ids)

if force_refresh:
    fetch_via_proxy.clear()

try:
    records = fetch_via_proxy(where)
    st.session_state["last_good_records"] = records
except Exception as e:
    st.warning(str(e))
    records = st.session_state.get("last_good_records", [])

st.sidebar.write("records:", len(records))

CLOSE_MIN = 1
for title, deps in build_board(records):
    st.markdown(f"### {title}")
    if not deps:
        st.caption("(geen realtime data)")
        continue

    lines = []
    for mins, line, dest in deps:
        mins_disp = "↓↓" if mins <= CLOSE_MIN else f"{mins:>2}"
        lines.append(f"{line:>2} {dest[:18]:<18} {mins_disp:>2}")
    st.code("\n".join(lines), language="text")