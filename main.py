import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

firebase_config = {
    "apiKey": "AIzaSyBOil40K2b-RiSVsBZVDs1MXoD7YtL_8es",
    "authDomain": "golden-time-48e25.firebaseapp.com",
    "databaseURL": "https://golden-time-48e25-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "golden-time-48e25",
    "storageBucket": "golden-time-48e25.firebasestorage.app",
    "messagingSenderId": "867094964354",
    "appId": "1:867094964354:web:afabf5c2fc9748503d6c9b"
}

# GPS
try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

# ---------------------------------------------------------
# 기본 설정
# ---------------------------------------------------------
st.set_page_config(page_title="골든 타임", layout="wide")

DEFAULT_LAT = 37.641240416205285
DEFAULT_LON = 126.93756984090838
DEFAULT_START_NAME = "하나고등학교"

HOTLINE = "010-5053-6831"

# ------------------------- TMAP API KEY -------------------------
TMAP_API_KEY = "c8j1Q7IvTe5MIuIDqIMbp69LUYkmbAMb5myniEQB"

# ---------------------------------------------------------
# CSS 스타일
# ---------------------------------------------------------
st.markdown("""
<style>
.main { background: #f5f7fb; }
.hero-card {
    background: white; padding: 26px 30px;
    border-radius: 18px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
    border: 1px solid #e5e9f2; text-align: center;
}
.hero-title { font-size: 38px; font-weight: 800; color: #111827; margin-bottom: 6px; }
.hero-subtitle { font-size: 17px; color: #4b5563; margin-bottom: 14px; }
.pill {
    display:inline-block; padding:4px 10px; border-radius:999px;
    background:#e5edff; color:#334e68; font-size:12px; margin:2px;
}
.section-card {
    background:white; padding:20px 22px; border-radius:16px;
    box-shadow:0 4px 16px rgba(15,23,42,0.08);
    border:1px solid #e5e9f2; margin-top:14px;
}
.section-title { font-size:18px; font-weight:700; margin-bottom:8px; color:#111827; }
.stButton>button {
    border-radius: 999px; font-size: 18px; padding: 10px 22px;
    border: none; font-weight: 600;
}
.mode-btn-hospital button { background: #0ea5e9; color: white; }
.mode-btn-ambulance button { background: #ef4444; color: white; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 병명 리스트
# ---------------------------------------------------------
DISEASES = [
    "심근경색", "뇌출혈", "뇌진탕", "심장마비",
    "뇌졸중", "급성 복막염", "기흉", "폐색전증",
    "패혈증", "급성 심부전", "뇌수막염",
    "대량 위장관 출혈", "아나필락시스"
]

def empty_treats():
    return {d: False for d in DISEASES}

def with_defaults(custom):
    base = empty_treats()
    base.update(custom)
    return base

# ---------------------------------------------------------
# 시술 리스트
# ---------------------------------------------------------
PROCEDURES = {
    "뇌출혈 개두술": "신경외과",
    "뇌진탕 모니터링": "신경외과",
    "뇌졸중 rtPA 투여": "신경외과",
    "심근경색 PCI": "순환기내과",
    "심부전 인공호흡기": "순환기내과",
    "기흉 흉관삽관": "흉부외과",
    "폐색전증 혈전용해술": "흉부외과",
    "패혈증 초기 치료": "응급의학과",
    "아나필락시스 응급처치": "응급의학과",
}

COLOR_MAP = {"o": "#16a34a", "x": "#dc2626", "Δ": "#facc15"}

# ---------------------------------------------------------
# 거리 계산
# ---------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat/2)**2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon/2)**2
    )
    return 2 * R * math.asin(math.sqrt(a))

def get_route_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
        data = requests.get(url, timeout=5).json()
        r = data["routes"][0]
        dist = r["distance"] / 1000
        eta = r["duration"] / 60
        path = [[c[0], c[1]] for c in r["geometry"]["coordinates"]]
        return dist, eta, path
    except:
        d = haversine(lat1, lon1, lat2, lon2)
        return d, d/50*60, [[lon1, lat1], [lon2, lat2]]

# ---------------------------------------------------------
# 세션 초기화
# ---------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"
# ---------------------------------------------------------
# 병원 데이터
# ---------------------------------------------------------
HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160, "lon": 126.9170,
        "address": "서울특별시 은평구 연서로 177",
        "phone": "02-111-2222",
        "website": "https://eph.yonsei.ac.kr",
        "treats_default": with_defaults({"뇌진탕": True, "뇌졸중": True}),
        "procedures": {
            "뇌출혈 개두술": "x",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "Δ",
            "심근경색 PCI": "x",
            "기흉 흉관삽관": "o",
        },
    },
    
    "서울대학교병원": {
        "lat": 37.57949411620278, "lon": 126.9988792235103,
        "address": "서울특별시 종로구 대학로 101",
        "phone": "1588-5700",
        "website": "https://eph.yonsei.ac.kr",
        "treats_default": with_defaults({
            "심근경색": True, "뇌출혈": True,"뇌진탕": True,
            "뇌졸중": True, "심장마비": True, "급성 복막염": True, 
            "기흉": True, "폐색전증": True,"패혈증": True, "급성 심부전": True,
            "뇌수막염": True, "대량 위장관 출혈": True, "아나필락시스": True}),
        "procedures": {
            "뇌출혈 개두술": "x",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "Δ",
            "심근경색 PCI": "x",
            "기흉 흉관삽관": "o",
        },
    },

    "가톨릭대 은평 성모병원": {
        "lat": 37.6370, "lon": 126.9190,
        "address": "서울특별시 은평구 통일로 1021",
        "phone": "02-222-3333",
        "website": "https://www.cmcseoul.or.kr",
        "treats_default": with_defaults({
            "심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True
        }),
        "procedures": {
            "뇌출혈 개두술": "o",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "o",
            "심근경색 PCI": "o",
            "기흉 흉관삽관": "o",
            "패혈증 초기 치료": "o",
            "아나필락시스 응급처치": "o",
        },
    },

    "서울 특별시 은평병원": {
        "lat": 37.5940039, "lon": 126.9232331,
        "address": "서울특별시 은평구 백련산로 90",
        "phone": "02-444-5555",
        "website": "http://epmhc.or.kr",
        "treats_default": with_defaults({
            "뇌출혈": True, "뇌진탕": True, "뇌졸중": True
        }),
        "procedures": {
            "뇌출혈 개두술": "o",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "o",
            "심근경색 PCI": "o",
            "기흉 흉관삽관": "o",
            "패혈증 초기 치료": "o",
            "아나필락시스 응급처치": "o",
        },
    },

    "본 서부병원": {
        "lat": 37.6050, "lon": 126.9090,
        "address": "서울특별시 은평구 은평로 133",
        "phone": "02-666-7777",
        "website": "http://www.bonseobu.com",
        "treats_default": with_defaults({
            "심근경색": True, "뇌진탕": True
        }),
        "procedures": {
            "뇌출혈 개두술": "o",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "o",
            "심근경색 PCI": "o",
            "기흉 흉관삽관": "o",
            "패혈증 초기 치료": "o",
            "아나필락시스 응급처치": "o",
        },
    },

    "청구 성심 병원": {
        "lat": 37.6290, "lon": 126.9220,
        "address": "서울특별시 은평구 통일로 873",
        "phone": "02-777-8888",
        "website": "http://www.chunggu.co.kr",
        "treats_default": with_defaults({
            "심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True
        }),
        "procedures": {
            "뇌출혈 개두술": "o",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "o",
            "심근경색 PCI": "o",
            "기흉 흉관삽관": "o",
            "패혈증 초기 치료": "o",
            "아나필락시스 응급처치": "o",
        },
    },

    "성누가병원": {
        "lat": 37.6099, "lon": 126.9293,
        "address": "서울특별시 은평구 281 102번지",
        "phone": "02-888-9999",
        "website": "https://example-snugcah.or.kr",
        "treats_default": with_defaults({
            "심근경색": True, "뇌졸중": True, "뇌출혈": True
        }),
        "procedures": {
            "뇌출혈 개두술": "o",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "o",
            "심근경색 PCI": "o",
            "기흉 흉관삽관": "o",
            "패혈증 초기 치료": "o",
            "아나필락시스 응급처치": "o",
        },
    },

    "리드힐병원": {
        "lat": 37.59980895027258, "lon": 126.91643982748181,
        "address": "서울특별시 은평구 연서로 10",
        "phone": "02-555-6666",
        "website": "http://m.leadheals.co.kr",
        "treats_default": with_defaults({
            "심근경색": True, "기흉": True, "폐색전증": True
        }),
        "procedures": {
            "뇌출혈 개두술": "o",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "o",
            "심근경색 PCI": "o",
            "기흉 흉관삽관": "o",
            "패혈증 초기 치료": "o",
            "아나필락시스 응급처치": "o",
        },
    },

    "연세노블병원": {
        "lat": 37.6018, "lon": 126.9270,
        "address": "서울특별시 은평구 녹번동 154-19",
        "phone": "02-999-0000",
        "website": "https://example-ynoble.or.kr",
        "treats_default": with_defaults({
            "뇌졸중": True, "뇌출혈": True, "뇌수막염": True
        }),
        "procedures": {
            "뇌출혈 개두술": "o",
            "뇌진탕 모니터링": "o",
            "뇌졸중 rtPA 투여": "o",
            "심근경색 PCI": "o",
            "기흉 흉관삽관": "o",
            "패혈증 초기 치료": "o",
            "아나필락시스 응급처치": "o",
        },
    },
}

# ---------------------------------------------------------
# 시술 표시 및 치료 가능 여부 세션 저장
# ---------------------------------------------------------
if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }

if "procedures" not in st.session_state:
    st.session_state.procedures = {
        h: dict(info["procedures"]) for h, info in HOSPITALS.items()
    }

# ---------------------------------------------------------
# HOME 화면
# ---------------------------------------------------------
if st.session_state.page == "home":
    col_l, col_c, col_r = st.columns([1, 2, 1])

    with col_c:
        st.markdown("""
        <div class="hero-card">
            <div class="hero-title">⏱ 골든 타임</div>
            <p class="hero-subtitle">은평권 응급 환자 이송 · 병원 매칭 시스템</p>
            <div>
                <span class="pill">하나고 기준</span>
                <span class="pill">실시간 경로 분석</span>
                <span class="pill">세부 시술 가능 여부</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="mode-btn-hospital">', unsafe_allow_html=True)
            if st.button("🏥 병원 모드", use_container_width=True):
                st.session_state.page = "hospital"
            st.markdown("</div>", unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="mode-btn-ambulance">', unsafe_allow_html=True)
            if st.button("🚑 구급차 모드", use_container_width=True):
                st.session_state.page = "ambulance"
            st.markdown("</div>", unsafe_allow_html=True)
# =========================================================
#                        병원 모드
# =========================================================
elif st.session_state.page == "hospital":

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader("🏥 병원 모드")
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # -----------------------------------------------------
    # 1. 병원 선택 + 치료 가능 병명 체크
    # -----------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">1. 병원 선택 및 수용 가능 병명 설정</div>', unsafe_allow_html=True)

    hospital = st.selectbox("병원을 선택하세요.", list(HOSPITALS.keys()))
    info = HOSPITALS[hospital]

    st.write("치료 가능한 병명을 체크해 주세요:")

    cols = st.columns(2)
    for idx, d in enumerate(DISEASES):
        with cols[idx % 2]:
            current = st.session_state.hospital_treats[hospital].get(d, False)
            new_val = st.checkbox(
                d,
                value=current,
                key=f"{hospital}_{d}",
            )
            st.session_state.hospital_treats[hospital][d] = new_val

    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # 2. 병원 정보 + 세부 시술 가능 여부
    # -----------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">2. 병원 정보 & 세부 시술 가능 여부</div>', unsafe_allow_html=True)

    st.write(f"**병원명:** {hospital}")
    st.write(f"**주소:** {info['address']}")

    # 대표전화 버튼
    st.markdown(
        f"""
        <a href="tel:{info['phone']}">
            <button style="padding:8px 18px;background:#2563EB;color:white;
                           border:none;border-radius:999px;font-size:15px;margin-top:6px;">
                📞 {info['phone']} 대표번호로 전화하기
            </button>
        </a>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------
    # 시술 가능 여부 (신호등 색)
    # -------------------------
    st.write("### 🩺 세부 시술/수술 가능 여부")

    proc_data = st.session_state.procedures[hospital]

    for proc, status in proc_data.items():
        color = COLOR_MAP.get(status, "#6b7280")
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;margin-bottom:6px;">
                <div style="width:14px;height:14px;border-radius:50%;background:{color};margin-right:8px;"></div>
                <span style="font-size:16px;">{proc}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------
    # 3. 병원 위치 지도 (PyDeck)
    # -----------------------------------------------------
    st.write("### 🗺 병원 위치")
    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": info["lat"], "lon": info["lon"]}],
        get_position="[lon, lat]",
        get_color=[239, 68, 68],
        get_radius=260,
    )
    view = pdk.ViewState(latitude=info["lat"], longitude=info["lon"], zoom=14)

    st.pydeck_chart(pdk.Deck(layers=[hospital_layer], initial_view_state=view))
    st.markdown("</div>", unsafe_allow_html=True)
# =========================================================
#                        구급차 모드
# =========================================================
elif st.session_state.page == "ambulance":

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader("🚑 구급차 모드")
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # -----------------------------------------------------
    # 1. 출발 위치
    # -----------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">1. 출발 위치 선택</div>', unsafe_allow_html=True)

    start_lat = DEFAULT_LAT
    start_lon = DEFAULT_LON
    start_name = DEFAULT_START_NAME

    st.write(f"기본 출발지: **{DEFAULT_START_NAME} (은평구 연서로 535)**")

    if GEO_AVAILABLE:
        st.info("📡 GPS 버튼을 누르면 현재 기기 위치를 사용합니다.")
        if st.button("📍 GPS로 현재 위치 가져오기"):
            loc = streamlit_geolocation()
            if isinstance(loc, dict) and loc.get("latitude"):
                start_lat = loc["latitude"]
                start_lon = loc["longitude"]
                start_name = "현재 위치"
                st.success(f"현재 위치 사용: 위도 {start_lat:.5f}, 경도 {start_lon:.5f}")
            else:
                st.warning("위치 정보를 가져오지 못했습니다.")
    else:
        st.info("⚠ GPS 기능을 사용하려면 streamlit-geolocation 설치가 필요합니다.")

    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # 2. 병명 선택
    # -----------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">2. 병명 선택</div>', unsafe_allow_html=True)

    disease = st.radio("환자의 병명을 선택하세요.", DISEASES, horizontal=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # 3. 수용 가능 병원 필터링
    # -----------------------------------------------------
    candidates = []

    for h, i in HOSPITALS.items():

        can_treat = st.session_state.hospital_treats.get(h, {}).get(disease, False)

        # 병명 → 필요한 시술 매핑
        required_procs = []
        if disease == "뇌출혈":
            required_procs = ["뇌출혈 개두술"]
        elif disease == "심근경색":
            required_procs = ["심근경색 PCI"]
        elif disease == "기흉":
            required_procs = ["기흉 흉관삽관"]
        elif disease == "패혈증":
            required_procs = ["패혈증 초기 치료"]

        proc_ok = True
        for rp in required_procs:
            if st.session_state.procedures[h].get(rp, "x") == "x":
                proc_ok = False

        if can_treat and proc_ok:
            dist, eta, _ = get_route_osrm(start_lat, start_lon, i["lat"], i["lon"])
            candidates.append({
                "병원": h,
                "거리(km)": round(dist, 2),
                "도착예상(분)": round(eta, 1),
                "address": i["address"],
                "phone": i["phone"],
                "website": i["website"],
                "lat": i["lat"],
                "lon": i["lon"],
            })

    # -----------------------------------------------------
    # 4. 병원 선택 테이블
    # -----------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">3. 수용 가능 병원 선택</div>', unsafe_allow_html=True)

    df = pd.DataFrame(candidates)

    if df.empty:
        st.error("🚫 해당 병명을 처리 가능한 병원이 없습니다.")
        st.stop()

    df = df.sort_values("도착예상(분)").reset_index(drop=True)
    display_df = df[["병원", "거리(km)", "도착예상(분)", "address", "phone"]]

    gob = GridOptionsBuilder.from_dataframe(display_df)
    gob.configure_selection("single", use_checkbox=True)

    grid = AgGrid(
        display_df,
        gridOptions=gob.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=260,
        theme="balham",
    )

    # ------------------------------
    # 🔥 오류 해결된 선택 로직
    # ------------------------------
    selected_rows = grid.get("selected_rows", [])

    # DataFrame이면 리스트로 변환
    if isinstance(selected_rows, pd.DataFrame):
        selected_rows = selected_rows.to_dict("records")

    # 길이 기반 체크 (if selected_rows ❌)
    if len(selected_rows) > 0:
        selected_name = selected_rows[0]["병원"]
    else:
        selected_name = df.iloc[0]["병원"]

    sel = df[df["병원"] == selected_name].iloc[0]

    st.markdown(
        f"**선택된 병원:** `{selected_name}` · 거리 **{sel['거리(km)']} km**, 예상 **{sel['도착예상(분)']} 분**"
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # 5. 연락 및 핫라인
    # -----------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">4. 연락 및 핫라인</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.write(f"📍 주소: {sel['address']}")
        st.markdown(
            f"""
            <a href="tel:{sel['phone']}">
                <button style="padding:8px 18px;background:#2563EB;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    📞 {sel['phone']} 병원 전화
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <a href="{sel['website']}" target="_blank">
                <button style="margin-top:6px;padding:8px 18px;background:#4B5563;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    🏥 홈페이지 열기
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.write("🚨 응급 핫라인")
        st.markdown(
            f"""
            <a href="tel:{HOTLINE}">
                <button style="padding:10px 22px;background:#DC2626;color:white;
                               border:none;border-radius:999px;font-size:17px;">
                    🚨 {HOTLINE} 즉시 전화
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------
    # 6. TMAP 지도 (길찾기 + 경로선 + 마커)
    # -----------------------------------------------------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">5. 지도 및 길안내 (Tmap)</div>', unsafe_allow_html=True)

    start_lat_js = start_lat
    start_lon_js = start_lon
    end_lat_js = sel["lat"]
    end_lon_js = sel["lon"]

    html_route = f"""
    <div id="route_map" style="width:100%; height:400px;"></div>

    <script src="https://apis.openapi.sk.com/tmap/jsv2?version=1&appKey={TMAP_API_KEY}"></script>

    <script>
        var startLat = {start_lat_js};
        var startLon = {start_lon_js};
        var endLat = {end_lat_js};
        var endLon = {end_lon_js};

        var map = new Tmapv2.Map("route_map", {{
            center: new Tmapv2.LatLng(startLat, startLon),
            width: "100%",
            height: "400px",
            zoom: 13
        }});

        new Tmapv2.Marker({{
            position: new Tmapv2.LatLng(startLat, startLon),
            icon: "http://tmapapi.sktelecom.com/upload/tmap/marker/pin_r_m_s.png",
            map: map
        }});

        new Tmapv2.Marker({{
            position: new Tmapv2.LatLng(endLat, endLon),
            icon: "http://tmapapi.sktelecom.com/upload/tmap/marker/pin_r_m_e.png",
            map: map
        }});

        function route() {{
            fetch("https://apis.openapi.sk.com/tmap/routes?version=1&format=json", {{
                method: "POST",
                headers: {{
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "appKey": "{TMAP_API_KEY}"
                }},
                body: JSON.stringify({{
                    startX: startLon.toString(),
                    startY: startLat.toString(),
                    endX: endLon.toString(),
                    endY: endLat.toString(),
                    reqCoordType: "WGS84GEO",
                    resCoordType: "WGS84GEO"
                }})
            }})
            .then(res => res.json())
            .then(data => drawRoute(data))
            .catch(err => console.log(err));
        }}

        function drawRoute(data) {{
            var lineArr = [];
            var features = data.features;

            for (var i in features) {{
                if (features[i].geometry.type === "LineString") {{
                    var coords = features[i].geometry.coordinates;
                    for (var j in coords) {{
                        lineArr.push(new Tmapv2.LatLng(coords[j][1], coords[j][0]));
                    }}
                }}
            }}

            new Tmapv2.Polyline({{
                path: lineArr,
                strokeColor: "#FF0000",
                strokeWeight: 5,
                map: map
            }});
        }}

        route();
    </script>
    """

    st.components.v1.html(html_route, height=400)
    st.markdown("</div>", unsafe_allow_html=True)
