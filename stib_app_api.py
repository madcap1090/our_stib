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

BASE_ODS = "https://data.stib-mivb.brussels/api/explore/v2.1/catalog/datasets/waiting-time-rt-production/records"
ODS_MIN_INTERVAL_S = 30  # <= 1 call per 30s per session


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def build_where_pointid_in(ids: list[str]) -> str:
    return f"pointid in ({', '.join(repr(s) for s in ids)})"


def _read(url: str, headers: dict, timeout: int = 30):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        text = raw.decode("utf-8", "ignore") if raw else ""
        return text


def fetch_ods_throttled(force: bool):
    """
    Enforces <= 1 ODS call per 30 seconds PER SESSION.
    If `force` is True (refresh button), bypass interval.
    """
    now = time.time()
    last_t = st.session_state.get("ods_last_fetch_ts", 0.0)

    if (not force) and (now - last_t) < ODS_MIN_INTERVAL_S:
        return st.session_state.get("ods_last_records", [])

    headers = {
        "User-Agent": "stib-streamlit/1.0",
        "Accept": "application/json",
        "Accept-Language": "nl,en;q=0.8,fr;q=0.6",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    ods_where = build_where_pointid_in(stop_ids)
    url = BASE_ODS + "?" + urllib.parse.urlencode({"limit": 100, "where": ods_where})

    for attempt in range(3):
        try:
            text = _read(url, headers=headers)
            payload = json.loads(text) if text.strip() else {}
            records = payload.get("results", [])

            st.session_state["ods_last_fetch_ts"] = now
            st.session_state["ods_last_records"] = records
            return records

        except urllib.error.HTTPError as e:
            body = e.read(2000).decode("utf-8", "ignore")
            if e.code == 429:
                reset = None
                try:
                    reset = json.loads(body).get("reset_time")
                except Exception:
                    pass
                st.warning(f"Rate limited (429). Reset: {reset or 'unknown'}")
                return st.session_state.get("ods_last_records", [])
            st.warning(f"ODS error {e.code}: {body[:200]}")
            time.sleep(1.5 * (attempt + 1))

        except urllib.error.URLError as e:
            st.warning(f"Network error: {e}")
            time.sleep(1.5 * (attempt + 1))

        except json.JSONDecodeError:
            st.warning("ODS did not return valid JSON.")
            time.sleep(1.5 * (attempt + 1))

    return st.session_state.get("ods_last_records", [])


def build_board(records):
    now = datetime.now().astimezone()
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

            mins = int((parse_dt(eta_s) - now).total_seconds() // 60)
            by_stop[sid].append((max(0, mins), line, dest))

    out = []
    for sid in stop_ids:
        title = stations[display].get(sid, sid)
        deps = sorted(by_stop[sid], key=lambda t: t[0])[:8]
        out.append((title, deps))
    return out


# ---------------- UI ----------------

st.set_page_config(page_title="STIB LCD", layout="centered")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1rem; padding-bottom: 1rem; }
      code { font-size: 22px !important; line-height: 1.25 !important; }

      /* Bigger refresh button */
      div.stButton > button {
        padding: 0.7rem 1.1rem !important;
        font-size: 1.25rem !important;
        border-radius: 0.75rem !important;
      }

      /* Small pad / spacing around top controls */
      .top-pad { margin: 0.25rem 0 0.75rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="top-pad"></div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 8], vertical_alignment="center")

force_refresh = False
with col1:
    if st.button("↻", help="Refresh"):
        force_refresh = True

with col2:
    st.caption(f"Last rerun: {datetime.now().isoformat(timespec='seconds')}")

records = fetch_ods_throttled(force=force_refresh)

CLOSE_MIN = 1
board = build_board(records)

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