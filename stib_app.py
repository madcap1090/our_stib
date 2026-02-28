import json
import ssl
import time
import urllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager

BRUSSELS = ZoneInfo("Europe/Brussels")

display = "nl"  # "nl" or "fr"

stations = {
    "fr": {"6803": "LENOIR", "1674": "BRUXELLOIS", "2506": "MIRRIOR", "1014": "MIRRIOR"},
    "nl": {"6803": "LENOIR", "1674": "BRUSSELAARS", "2506": "SPIEGEL", "1014": "SPIEGEL"},
}

stop_ids = list(stations["fr"].keys())

BASE_ODS = "https://data.stib-mivb.brussels/api/explore/v2.1/catalog/datasets/waiting-time-rt-production/records"
BASE_AZ = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb/rt/WaitingTimes/"

ODS_MIN_INTERVAL_S = 30  # <= 1 call per 30s per session


def _read(url: str, headers: dict, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        return raw.decode("utf-8", "ignore") if raw else ""

def parse_dt(s: str) -> datetime:
    # ODS often returns ...Z; fromisoformat doesn't like 'Z'
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    # If it's naive for some reason, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt


def build_where_pointid(ids: list[str]) -> str:
    return " OR ".join(f'pointid="{x}"' for x in ids)

class TLSAdapter(HTTPAdapter):
    """
    Requests adapter with a custom SSLContext.
    Tries to work around OpenSSL strictness / TLS quirks on hosted platforms.
    """
    def __init__(self, ssl_context: ssl.SSLContext, **kwargs):
        self._ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["ssl_context"] = self._ssl_context
        self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize, block=block, **pool_kwargs)


def make_session() -> requests.Session:
    ctx = ssl.create_default_context()

    # Relax cipher policy a bit (helps on some OpenSSL 3 environments)
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    except Exception:
        pass

    # Pin to TLS 1.2 (avoid TLS 1.3 negotiation weirdness)
    if hasattr(ssl, "TLSVersion"):
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        except Exception:
            pass

    s = requests.Session()
    s.mount("https://", TLSAdapter(ctx))
    return s


@st.cache_resource
def get_session() -> requests.Session:
    return make_session()


def fetch_ods_throttled(force: bool):
    now = time.time()
    last_t = st.session_state.get("ods_last_fetch_ts", 0.0)

    if (not force) and (now - last_t) < ODS_MIN_INTERVAL_S:
        return st.session_state.get("ods_last_records", [])

    headers = {
        "User-Agent": "stib-streamlit/1.0",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "bmc-partner-key": st.secrets["BMC_PARTNER_KEY"].strip(),
    }

    where = build_where_pointid(stop_ids)
    where = "pointid IN (\"6803\",\"1674\",\"2506\",\"1014\")"
    
    
    url = BASE_AZ + "?" + urlencode(
    {"limit": 100, "where": where},
    quote_via=quote,  # encodes spaces as %20, not +
    )

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
            st.warning(f"API error {e.code}: {body[:200]}")
            time.sleep(1.5 * (attempt + 1))

        except urllib.error.URLError as e:
            st.warning(f"Network error: {e}")
            time.sleep(1.5 * (attempt + 1))

        except json.JSONDecodeError:
            st.warning("API did not return valid JSON.")
            time.sleep(1.5 * (attempt + 1))

    return st.session_state.get("ods_last_records", [])


def build_board(records):
    now = datetime.now(BRUSSELS)
    by_stop = {sid: [] for sid in stop_ids}

    for rec in records:
        sid = str(rec.get("pointid"))
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

records = fetch_ods_throttled(force=force_refresh)
records = [r for r in records if str(r.get("pointid")) in set(stop_ids)]

st.sidebar.write("records:", len(records))

if records:
    st.sidebar.write("sample pointid type/value:", type(records[0].get("pointid")).__name__, records[0].get("pointid"))

wanted = set(stop_ids)
st.sidebar.write("unique pointids (first 10):", sorted({str(r.get("pointid")) for r in records})[:10])

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