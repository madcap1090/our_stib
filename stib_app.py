import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

BRUSSELS = ZoneInfo("Europe/Brussels")

display = "nl"
stations = {
    "fr": {"6803": "LENOIR", "1674": "BRUXELLOIS", "2506": "MIRRIOR", "1014": "MIRRIOR"},
    "nl": {"6803": "LENOIR", "1674": "BRUSSELAARS", "2506": "SPIEGEL", "1014": "SPIEGEL"},
}
stop_ids = list(stations["fr"].keys())

BASE_ODS = "https://stibmivb.opendatasoft.com/api/explore/v2.1/catalog/datasets/waiting-time-rt-production/records"
CACHE_TTL_S = 60  # be kinder to quota

def parse_dt(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt

def build_where_pointid_in(ids: list[str]) -> str:
    return f"pointid in ({', '.join(repr(s) for s in ids)})"

def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {}

@st.cache_resource
def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "stib-streamlit/1.0"})
    return s

@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def fetch_ods_cached(where: str) -> list[dict]:
    params = {"limit": 100, "where": where}
    headers = {
        "Accept": "application/json",
        "Accept-Language": "nl,en;q=0.8,fr;q=0.6",
    }

    api_key = st.secrets.get("STIB_API_KEY")
    if api_key:
        headers["Authorization"] = f"Apikey {api_key}"  # keep key OUT of URL

    s = get_session()

    last_exc = None
    for attempt in range(3):
        try:
            r = s.get(BASE_ODS, params=params, headers=headers, timeout=30)
            break
        except requests.exceptions.SSLError as e:
            last_exc = e
            time.sleep(1.5 * (attempt + 1))
    else:
        raise last_exc

    if r.status_code == 429:
        data = safe_json(r)
        raise RuntimeError(f"429 reset_time={data.get('reset_time')} body={data}")

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

# UI
st.set_page_config(page_title="STIB LCD", layout="centered")

api_key = st.secrets.get("STIB_API_KEY")
st.sidebar.write("STIB_API_KEY loaded:", bool(api_key))

force_refresh = st.button("↻", help="Refresh")

where = build_where_pointid_in(stop_ids)

if force_refresh:
    fetch_ods_cached.clear()

try:
    records = fetch_ods_cached(where)
    st.session_state["last_good_records"] = records
except Exception as e:
    st.warning(str(e))
    records = st.session_state.get("last_good_records", [])

st.sidebar.write("records:", len(records))

for title, deps in build_board(records):
    st.markdown(f"### {title}")
    if not deps:
        st.caption("(geen realtime data)")
        continue
    lines = []
    for mins, line, dest in deps:
        mins_disp = "↓↓" if mins <= 1 else f"{mins:>2}"
        lines.append(f"{line:>2} {dest[:18]:<18} {mins_disp:>2}")
    st.code("\n".join(lines), language="text")