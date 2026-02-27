import json
import time
from datetime import datetime

import streamlit as st
import requests
import ssl
from zoneinfo import ZoneInfo

BRUSSELS = ZoneInfo("Europe/Brussels")

display = "nl"  # "nl" or "fr"

stations = {
    "fr": {"6803": "LENOIR", "1674": "BRUXELLOIS", "2506": "MIRRIOR", "1014": "MIRRIOR"},
    "nl": {"6803": "LENOIR", "1674": "BRUSSELAARS", "2506": "SPIEGEL", "1014": "SPIEGEL"},
}
stop_ids = list(stations["fr"].keys())

BASE_ODS = "https://data.stib-mivb.brussels/api/explore/v2.1/catalog/datasets/waiting-time-rt-production/records"
CACHE_TTL_S = 30  # shared cache across users (prevents per-user spam / shared-IP 429s)


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
class TLSAdapter(HTTPAdapter):
    """Requests adapter with a custom SSLContext (handy on some hosted OpenSSL setups)."""

    def __init__(self, ssl_context: ssl.SSLContext, **kwargs):
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["ssl_context"] = self._ssl_context
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs
        )


@st.cache_resource
def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "stib-streamlit/1.0"})
    return s


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def fetch_ods_cached(where: str) -> list[dict]:
    params = {"limit": 100, "where": where}

    headers = {
        "User-Agent": "stib-streamlit/1.0",
        "Accept": "application/json",
        "Accept-Language": "nl,en;q=0.8,fr;q=0.6",
    }

    api_key = st.secrets.get("STIB_API_KEY")
    if api_key:
        headers["Authorization"] = f"Apikey {api_key}"

    s = get_session()
    r = s.get(BASE_ODS, params=params, headers=headers, timeout=30)

    for attempt in range(3):
        try:
            r = s.get(BASE_ODS, params=params, headers=headers, timeout=30)
            break
        except requests.exceptions.SSLError:
            time.sleep(1.5 * (attempt + 1))
    else:
        raise

    if r.status_code == 429:
        data = safe_json(r)
        raise RuntimeError(
            "Rate limited (429). "
            f"reset_time={data.get('reset_time')} "
            f"Retry-After={r.headers.get('Retry-After')} "
            f"Remaining={r.headers.get('X-RateLimit-Remaining')} "
            f"Limit={r.headers.get('X-RateLimit-Limit')}"
        )

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

api_key = st.secrets.get("STIB_API_KEY")
st.sidebar.write("STIB_API_KEY loaded:", bool(api_key))

st.markdown(
    """
    <style>
      .block-container { padding-top: 3rem; padding-bottom: 1rem; }
      code { font-size: 22px !important; line-height: 1.25 !important; }
      div.stButton > button {
        padding: 0.7rem 1.1rem !important;
        font-size: 1.25rem !important;
        border-radius: 0.75rem !important;
      }
      .top-pad { margin: 0.25rem 0 0.75rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1, 8], vertical_alignment="center")

force_refresh = False
with col1:
    if st.button("↻", help="Refresh"):
        force_refresh = True

with col2:
    st.caption(f"Last rerun: {datetime.now(BRUSSELS).isoformat(timespec='seconds')}")

where = build_where_pointid_in(stop_ids)

if force_refresh:
    # blow the shared cache and immediately refetch
    fetch_ods_cached.clear()

try:
    records = fetch_ods_cached(where)
    st.session_state["last_good_records"] = records
except Exception as e:
    st.warning(str(e))
    records = st.session_state.get("last_good_records", [])

CLOSE_MIN = 1
board = build_board(records)

st.sidebar.write("records:", len(records))
st.sidebar.write("cache ttl (s):", CACHE_TTL_S)

# Helpful warning if key is missing (optional)
if not st.secrets.get("STIB_API_KEY", ""):
    st.warning("No STIB_API_KEY found in .streamlit/secrets.toml (requests will be anonymous and rate-limited faster).")

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