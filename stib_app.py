import json
import urllib.parse
import urllib.request
from datetime import datetime
import time
import urllib.error


import streamlit as st

display = "nl"  # "nl" or "fr"

stations = {
    "fr": {"6803": "LENOIR", "1674": "BRUXELLOIS", "2506": "MIRRIOR", "1014": "MIRRIOR"},
    "nl": {"6803": "LENOIR", "1674": "BRUSSELAARS", "2506": "SPIEGEL", "1014": "SPIEGEL"},
}
stop_ids = list(stations["fr"].keys())

BASE = "https://data.stib-mivb.brussels/api/explore/v2.1/catalog/datasets/waiting-time-rt-production/records"

def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)

@st.cache_data(ttl=10)
def fetch_results():
    where = f"pointid in ({', '.join(repr(s) for s in stop_ids)})"
    url = BASE + "?" + urllib.parse.urlencode({"limit": 200, "where": where})

    # Some gateways dislike plain urllib; these headers usually help
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; stib-streamlit/1.0)",
        "Accept": "application/json",
        "Accept-Language": "nl,en;q=0.8,fr;q=0.6",
    }

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp).get("results", [])
        except urllib.error.HTTPError as e:
            # show status + a short snippet so you can debug (safe)
            body = e.read(300).decode("utf-8", "ignore")
            st.warning(f"STIB API error {e.code}: {body[:200]}")
            last_err = e
            time.sleep(1.5 * (attempt + 1))
        except Exception as e:
            st.warning(f"Network error: {type(e).__name__}: {e}")
            last_err = e
            time.sleep(1.5 * (attempt + 1))

    # Don’t crash the app
    return []
def build_board(results):
    now = datetime.now().astimezone()
    by_stop = {sid: [] for sid in stop_ids}

    for rec in results:
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

            mins = int((parse_dt(eta_s) - now).total_seconds() // 60)
            mins = max(0, mins)
            by_stop[sid].append((mins, line, dest))

    out = []
    for sid in stop_ids:
        title = stations[display].get(sid, sid)
        deps = sorted(by_stop[sid], key=lambda t: t[0])[:8]
        out.append((title, deps))
    return out

st.set_page_config(page_title="STIB LCD", layout="centered")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1rem; padding-bottom: 1rem; }
      code { font-size: 22px !important; line-height: 1.25 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

refresh = st.slider("Refresh (seconds)", 5, 60, 15)
st.markdown(f"<meta http-equiv='refresh' content='{refresh}'>", unsafe_allow_html=True)

CLOSE_MIN = 1

board = build_board(fetch_results())
for title, deps in board:
    st.markdown(f"### {title}")
    if not deps:
        st.caption("(geen realtime data)")
        continue

    lines = []
    for mins, line, dest in deps:
        mins_disp = "↓↓" if mins <= CLOSE_MIN else f"{mins:>2}"
        lines.append(f"{line:>2} {dest[:18]:<18} {mins_disp:>2}")
    st.code("\n".join(lines), language="text")