import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# GPS 컴포넌트 (설치 안 되어 있어도 앱은 돌아가게 처리)
try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

# ------------------------------------------
# 기본 설정
# ------------------------------------------
st.set_page_config(page_title="골든 타임", layout="wide")

# 기본 출발 위치: 하나고
DEFAULT_LAT = 37.641240416205285
DEFAULT_LON = 126.93756984090838
DEFAULT_START_NAME = "하나고등학교"

HOTLINE = "010-5053-6831"

# ------------------------------------------
# 전역 간단 스타일 (이전 느낌으로 단순화)
# ------------------------------------------
st.markdown(
    """
    <style>
    .main {
        background: #f5f7fb;
    }
    .hero-card {
        background: white;
        padding: 26px 30px;
        border-radius: 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        border: 1px solid #e5e9f2;
        text-align: center;
    }
    .hero-title {
        font-size: 38px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 6px;
    }
    .hero-subtitle {
        font-size: 17px;
        color: #4b5563;
        margin-bottom: 14px;
    }
    .pill {
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        background:#e5edff;
        color:#334e68;
        font-size:12px;
        margin:2px;
    }
    .section-card {
        background:white;
        padding:20px 22px;
        border-radius:16px;
        box-shadow:0 4px 16px rgba(15,23,42,0.08);
        border:1px solid #e5e9f2;
        margin-top:14px;
    }
    .section-title {
        font-size:18px;
        font-weight:700;
        margin-bottom:8px;
        color:#111827;
    }
    .stButton>button {
        border-radius: 999px;
        font-size: 18px;
        padding: 10px 22px;
        border: none;
        font-weight: 600;
    }
    .mode-btn-hospital button {
        background: #0ea5e9;
        color: white;
    }
    .mode-btn-ambulance button {
        background: #ef4444;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 병명 리스트 (발작 제거)
DISEASES = [
    "심근경색",
    "뇌출혈",
    "뇌진탕",
    "심장마비",
    "뇌졸중",
    "급성 복막염",
    "기흉",
    "폐색전증",
    "패혈증",
    "급성 심부전",
    "뇌수막염",
    "대량 위장관 출혈",
    "아나필락시스",
]

def empty_treats():
    return {d: False for d in DISEASES}

def with_defaults(custom_dict):
    base = empty_treats()
    base.update(custom_dict)
    return base

HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160,
        "lon": 126.9170,
        "address": "서울특별시 은평구 연서로 177",
        "phone": "02-111-2222",
        "website": "https://eph.yonsei.ac.kr",
        "treats_default": with_defaults(
            {"뇌진탕": True, "뇌졸중": True}
        ),
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370,
        "lon": 126.9190,
        "address": "서울특별시 은평구 통일로 1021",
        "phone": "02-222-3333",
        "website": "https://www.cmcseoul.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True}
        ),
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,
        "lon": 126.9232331,
        "address": "서울특별시 은평구 백련산로 90",
        "phone": "02-444-5555",
        "website": "http://epmhc.or.kr",
        "treats_default": with_defaults(
            {"뇌출혈": True, "뇌진탕": True, "뇌졸중": True}
        ),
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "address": "서울특별시 은평구 은평로 133",
        "phone": "02-666-7777",
        "website": "http://seobuhospital.co.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌진탕": True}
        ),
    },
    "청구 성심 병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "address": "서울특별시 은평구 통일로 873",
        "phone": "02-777-8888",
        "website": "http://www.chunggu.co.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True}
        ),
    },
    "성누가병원": {
        "lat": 37.6099,
        "lon": 126.9293,
        "address": "서울특별시 은평구 281 102번지",
        "phone": "02-888-9999",
        "website": "https://example-snugcah.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌졸중": True, "뇌출혈": True}
        ),
    },
    "리드힐병원": {
        "lat": 37.6203,
        "lon": 126.9299,
        "address": "서울특별시 은평구 연서로 10",
        "phone": "02-555-6666",
        "website": "https://example-leadhill.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "기흉": True, "폐색전증": True}
        ),
    },
    "연세노블병원": {
        "lat": 37.6018,
        "lon": 126.9270,
        "address": "서울특별시 은평구 녹번동 154-19",
        "phone": "02-999-0000",
        "website": "https://example-ynoble.or.kr",
        "treats_default": with_defaults(
            {"뇌졸중": True, "뇌출혈": True, "뇌수막염": True}
        ),
    },
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))

def get_route_osrm(lat1, lon1, lat2, lon2):
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )
    try:
        res = requests.get(url, timeout=5).json()
        route = res["routes"][0]
        coords = route["geometry"]["coordinates"]
        dist = route["distance"] / 1000
        eta = route["duration"] / 60
        path = [[c[0], c[1]] for c in coords]
        return dist, eta, path
    except Exception:
        d = haversine(lat1, lon1, lat2, lon2)
        return d, d / 50 * 60, [[lon1, lat1], [lon2, lat2]]

if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }
else:
    for h, info in HOSPITALS.items():
        if h not in st.session_state.hospital_treats:
            st.session_state.hospital_treats[h] = dict(info["treats_default"])
        else:
            for d in DISEASES:
                st.session_state.hospital_treats[h].setdefault(d, False)

# (중략: home / hospital 모드는 기존과 동일)

# --- 구급차 모드 (ambulance) 부분에서, naver map 링크 생성 수정 ---
elif st.session_state.page == "ambulance":
    # (위 코드는 기존 그대로)

    # 네이버 지도 길찾기 URL 생성 (출발지 포함)
    nmap_url = (
        "nmap://route/car?"
        f"slat={start_lat}&slng={start_lon}&sname={start_name}&"
        f"dlat={sel['lat']}&dlng={sel['lon']}&dname={selected_name}&"
        f"appname=goldentime"
    )

    web_url = (
        "https://map.naver.com/v5/directions/-/-/"
        f"{start_lon},{start_lat}/{sel['lon']},{sel['lat']}/0?c=14,0,0,0,dh"
    )

    st.markdown(
        f"""
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;">
            <a href="{nmap_url}">
                <button style="padding:9px 18px;background:#03C75A;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    🧭 네이버 지도 앱으로 길찾기
                </button>
            </a>
            <a href="{web_url}" target="_blank">
                <button style="padding:9px 18px;background:#111827;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    🌐 브라우저에서 네이버 지도 열기
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# GPS 컴포넌트 (설치 안 되어 있어도 앱은 돌아가게 처리)
try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

# ------------------------------------------
# 기본 설정
# ------------------------------------------
st.set_page_config(page_title="골든 타임", layout="wide")

# 기본 출발 위치: 하나고
DEFAULT_LAT = 37.641240416205285
DEFAULT_LON = 126.93756984090838
DEFAULT_START_NAME = "하나고등학교"

HOTLINE = "010-5053-6831"

# ------------------------------------------
# 전역 간단 스타일 (이전 느낌으로 단순화)
# ------------------------------------------
st.markdown(
    """
    <style>
    .main {
        background: #f5f7fb;
    }
    .hero-card {
        background: white;
        padding: 26px 30px;
        border-radius: 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        border: 1px solid #e5e9f2;
        text-align: center;
    }
    .hero-title {
        font-size: 38px;
        font-weight: 800;
        color: #111827;
        margin-bottom: 6px;
    }
    .hero-subtitle {
        font-size: 17px;
        color: #4b5563;
        margin-bottom: 14px;
    }
    .pill {
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        background:#e5edff;
        color:#334e68;
        font-size:12px;
        margin:2px;
    }
    .section-card {
        background:white;
        padding:20px 22px;
        border-radius:16px;
        box-shadow:0 4px 16px rgba(15,23,42,0.08);
        border:1px solid #e5e9f2;
        margin-top:14px;
    }
    .section-title {
        font-size:18px;
        font-weight:700;
        margin-bottom:8px;
        color:#111827;
    }
    .stButton>button {
        border-radius: 999px;
        font-size: 18px;
        padding: 10px 22px;
        border: none;
        font-weight: 600;
    }
    .mode-btn-hospital button {
        background: #0ea5e9;
        color: white;
    }
    .mode-btn-ambulance button {
        background: #ef4444;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 병명 리스트 (발작 제거)
DISEASES = [
    "심근경색",
    "뇌출혈",
    "뇌진탕",
    "심장마비",
    "뇌졸중",
    "급성 복막염",
    "기흉",
    "폐색전증",
    "패혈증",
    "급성 심부전",
    "뇌수막염",
    "대량 위장관 출혈",
    "아나필락시스",
]

def empty_treats():
    return {d: False for d in DISEASES}

def with_defaults(custom_dict):
    base = empty_treats()
    base.update(custom_dict)
    return base

HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160,
        "lon": 126.9170,
        "address": "서울특별시 은평구 연서로 177",
        "phone": "02-111-2222",
        "website": "https://eph.yonsei.ac.kr",
        "treats_default": with_defaults(
            {"뇌진탕": True, "뇌졸중": True}
        ),
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370,
        "lon": 126.9190,
        "address": "서울특별시 은평구 통일로 1021",
        "phone": "02-222-3333",
        "website": "https://www.cmcseoul.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True}
        ),
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,
        "lon": 126.9232331,
        "address": "서울특별시 은평구 백련산로 90",
        "phone": "02-444-5555",
        "website": "http://epmhc.or.kr",
        "treats_default": with_defaults(
            {"뇌출혈": True, "뇌진탕": True, "뇌졸중": True}
        ),
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "address": "서울특별시 은평구 은평로 133",
        "phone": "02-666-7777",
        "website": "http://seobuhospital.co.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌진탕": True}
        ),
    },
    "청구 성심 병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "address": "서울특별시 은평구 통일로 873",
        "phone": "02-777-8888",
        "website": "http://www.chunggu.co.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True}
        ),
    },
    "성누가병원": {
        "lat": 37.6099,
        "lon": 126.9293,
        "address": "서울특별시 은평구 281 102번지",
        "phone": "02-888-9999",
        "website": "https://example-snugcah.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌졸중": True, "뇌출혈": True}
        ),
    },
    "리드힐병원": {
        "lat": 37.6203,
        "lon": 126.9299,
        "address": "서울특별시 은평구 연서로 10",
        "phone": "02-555-6666",
        "website": "https://example-leadhill.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "기흉": True, "폐색전증": True}
        ),
    },
    "연세노블병원": {
        "lat": 37.6018,
        "lon": 126.9270,
        "address": "서울특별시 은평구 녹번동 154-19",
        "phone": "02-999-0000",
        "website": "https://example-ynoble.or.kr",
        "treats_default": with_defaults(
            {"뇌졸중": True, "뇌출혈": True, "뇌수막염": True}
        ),
    },
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))

def get_route_osrm(lat1, lon1, lat2, lon2):
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )
    try:
        res = requests.get(url, timeout=5).json()
        route = res["routes"][0]
        coords = route["geometry"]["coordinates"]
        dist = route["distance"] / 1000
        eta = route["duration"] / 60
        path = [[c[0], c[1]] for c in coords]
        return dist, eta, path
    except Exception:
        d = haversine(lat1, lon1, lat2, lon2)
        return d, d / 50 * 60, [[lon1, lat1], [lon2, lat2]]

if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }
else:
    for h, info in HOSPITALS.items():
        if h not in st.session_state.hospital_treats:
            st.session_state.hospital_treats[h] = dict(info["treats_default"])
        else:
            for d in DISEASES:
                st.session_state.hospital_treats[h].setdefault(d, False)

# (중략: home / hospital 모드는 기존과 동일)

# --- 구급차 모드 (ambulance) 부분에서, naver map 링크 생성 수정 ---
elif st.session_state.page == "ambulance":
    # (위 코드는 기존 그대로)

    # 네이버 지도 길찾기 URL 생성 (출발지 포함)
    nmap_url = (
        "nmap://route/car?"
        f"slat={start_lat}&slng={start_lon}&sname={start_name}&"
        f"dlat={sel['lat']}&dlng={sel['lon']}&dname={selected_name}&"
        f"appname=goldentime"
    )

    web_url = (
        "https://map.naver.com/v5/directions/-/-/"
        f"{start_lon},{start_lat}/{sel['lon']},{sel['lat']}/0?c=14,0,0,0,dh"
    )

    st.markdown(
        f"""
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;">
            <a href="{nmap_url}">
                <button style="padding:9px 18px;background:#03C75A;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    🧭 네이버 지도 앱으로 길찾기
                </button>
            </a>
            <a href="{web_url}" target="_blank">
                <button style="padding:9px 18px;background:#111827;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    🌐 브라우저에서 네이버 지도 열기
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
