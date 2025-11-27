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

# ------------------------------------------
# 병명 리스트
# ------------------------------------------
DISEASES = [
    "심근경색", "뇌출혈", "뇌진탕", "심장마비", "뇌졸중",
    "급성 복막염", "기흉", "폐색전증", "패혈증", "급성 심부전",
    "뇌수막염", "대량 위장관 출혈", "아나필락시스",
]

def empty_treats():
    return {d: False for d in DISEASES}

def with_defaults(custom_dict):
    base = empty_treats()
    base.update(custom_dict)
    return base

# ------------------------------------------
# 병원 데이터
# ------------------------------------------
HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160,
        "lon": 126.9170,
        "address": "서울특별시 은평구 연서로 177",
        "phone": "02-111-2222",
        "website": "https://eph.yonsei.ac.kr",
        "treats_default": with_defaults({"뇌진탕": True, "뇌졸중": True}),
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370,
        "lon": 126.9190,
        "address": "서울특별시 은평구 통일로 1021",
        "phone": "02-222-3333",
        "website": "https://www.cmcseoul.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True}),
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,
        "lon": 126.9232331,
        "address": "서울특별시 은평구 백련산로 90",
        "phone": "02-444-5555",
        "website": "http://epmhc.or.kr",
        "treats_default": with_defaults(
            {"뇌출혈": True, "뇌진탕": True, "뇌졸중": True}),
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "address": "서울특별시 은평구 은평로 133",
        "phone": "02-666-7777",
        "website": "http://seobuhospital.co.kr",
        "treats_default": with_defaults({"심근경색": True, "뇌진탕": True}),
    },
    "청구 성심 병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "address": "서울특별시 은평구 통일로 873",
        "phone": "02-777-8888",
        "website": "http://www.chunggu.co.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌출혈": True, "뇌졸중": True, "심장마비": True}),
    },
    "성누가병원": {
        "lat": 37.6099,
        "lon": 126.9293,
        "address": "서울특별시 은평구 281 102번지",
        "phone": "02-888-9999",
        "website": "https://example-snugcah.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌졸중": True, "뇌출혈": True}),
    },
    "리드힐병원": {
        "lat": 37.6203,
        "lon": 126.9299,
        "address": "서울특별시 은평구 연서로 10",
        "phone": "02-555-6666",
        "website": "https://example-leadhill.or.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "기흉": True, "폐색전증": True}),
    },
    "연세노블병원": {
        "lat": 37.6018,
        "lon": 126.9270,
        "address": "서울특별시 은평구 녹번동 154-19",
        "phone": "02-999-0000",
        "website": "https://example-ynoble.or.kr",
        "treats_default": with_defaults(
            {"뇌졸중": True, "뇌출혈": True, "뇌수막염": True}),
    },
}

# ------------------------------------------
# 거리 계산
# ------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2)**2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2)**2
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

# ------------------------------------------
# 세션 상태
# ------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }

# ==========================================================
# HOME 화면
# ==========================================================
if st.session_state.page == "home":
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div class="hero-card">
                <div class="hero-title">⏱ 골든 타임</div>
                <p class="hero-subtitle">은평권 응급 환자 이송 · 병원 매칭 시스템</p>
                <div>
                    <span class="pill">하나고 출발 기준</span>
                    <span class="pill">도로 기준 최적 경로</span>
                    <span class="pill">병원 수용 가능 병명 사전 체크</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
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

# ==========================================================
# 병원 모드
# ==========================================================
elif st.session_state.page == "hospital":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader("🏥 병원 모드")
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # 병원 선택
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">1. 병원 선택 및 병명 설정</div>', unsafe_allow_html=True)

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

    # 병원 정보
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">2. 병원 정보</div>', unsafe_allow_html=True)
    st.write(f"**병원명:** {hospital}")
    st.write(f"**주소:** {info['address']}")

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

    st.write("")
    st.write("**위치 지도**")

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

# ==========================================================
# 구급차 모드
# ==========================================================
elif st.session_state.page == "ambulance":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader("🚑 구급차 모드")
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # 1. 출발 위치
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
            if isinstance(loc, dict) and loc.get("latitude") and loc.get("longitude"):
                start_lat = loc["latitude"]
                start_lon = loc["longitude"]
                start_name = "현재 위치"
                st.success(f"현재 위치 사용: 위도 {start_lat:.5f}, 경도 {start_lon:.5f}")
            else:
                st.warning("위치 정보를 가져오지 못했습니다. 기본 위치(하나고)를 계속 사용합니다.")
    st.markdown("</div>", unsafe_allow_html=True)

    # 2. 병명
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">2. 병명 선택</div>', unsafe_allow_html=True)

    disease = st.radio("환자의 병명을 선택하세요.", DISEASES, horizontal=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # 3. 치료 가능 병원 필터링
    candidates = []
    for h, i in HOSPITALS.items():
        can_treat = st.session_state.hospital_treats.get(h, {}).get(disease, False)
        if can_treat:
            dist, eta, _ = get_route_osrm(start_lat, start_lon, i["lat"], i["lon"])
            candidates.append(
                {
                    "병원": h,
                    "거리(km)": round(dist, 2),
                    "도착예상(분)": round(eta, 1),
                    "address": i["address"],
                    "phone": i["phone"],
                    "website": i["website"],
                    "lat": i["lat"],
                    "lon": i["lon"],
                }
            )

    # 병원 선택 테이블
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">3. 수용 가능 병원 선택</div>', unsafe_allow_html=True)

    df = pd.DataFrame(candidates)

    if df.empty:
        st.error("🚫 이 병명을 현재 치료 가능으로 체크한 병원이 없습니다.")
        st.table(pd.DataFrame([{"병원": "병원 없음"}]))
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    df = df.sort_values("도착예상(분)").reset_index(drop=True)
    display_df = df[["병원", "거리(km)", "도착예상(분)", "address", "phone"]]

    gob = GridOptionsBuilder.from_dataframe(display_df)
    gob.configure_selection("single", use_checkbox=True)
    gob.configure_pagination(enabled=True, paginationAutoPageSize=True)

    grid = AgGrid(
        display_df,
        gridOptions=gob.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=260,
        theme="balham",
    )

    raw_sel = grid.get("selected_rows", [])

    if isinstance(raw_sel, list) and len(raw_sel) > 0:
        selected_name = raw_sel[0]["병원"]
    else:
        selected_name = df.iloc[0]["병원"]

    sel = df[df["병원"] == selected_name].iloc[0]

    st.markdown(
        f"**선택된 병원:** `{selected_name}` · 거리 약 **{sel['거리(km)']} km**, "
        f"예상 **{sel['도착예상(분)']} 분**"
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # 4. 연락
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">4. 연락 및 핫라인</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"📍 **주소:** {sel['address']}")
        st.markdown(
            f"""
            <a href="tel:{sel['phone']}">
                <button style="padding:8px 18px;background:#2563EB;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    📞 {sel['phone']} 병원으로 전화하기
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
                    🏥 병원 홈페이지 열기
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.write("🚨 **응급 핫라인**")
        st.markdown(
            f"""
            <a href="tel:{HOTLINE}">
                <button style="padding:10px 22px;background:#DC2626;color:white;
                               border:none;border-radius:999px;font-size:17px;">
                    🚨 {HOTLINE} 으로 즉시 전화
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # 5. 지도 (Google Maps)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">5. 지도 및 길안내</div>', unsafe_allow_html=True)

    dist, eta, path = get_route_osrm(start_lat, start_lon, sel["lat"], sel["lon"])

    st.write(
        f"🛣 도로 기준 거리: **{round(dist,2)} km**, 예상 소요 시간: **{round(eta,1)} 분**"
    )
    st.write(f"출발지: **{start_name}**")

    GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAP_API_KEY"

    google_map_html = f"""
    <div id="map" style="height:520px; width:100%; border-radius:16px;"></div>

    <script>
    function initMap() {{
        const start = {{ lat: {start_lat}, lng: {start_lon} }};
        const end = {{ lat: {sel['lat']}, lng: {sel['lon']} }};

        const map = new google.maps.Map(document.getElementById("map"), {{
            zoom: 13,
            center: start,
            mapTypeId: 'roadmap',
            styles: [
                {{
                    "featureType": "all",
                    "elementType": "geometry",
                    "stylers": [{{ "color": "#eaeff5" }}]
                }},
                {{
                    "featureType": "road",
                    "elementType": "geometry",
                    "stylers": [{{ "color": "#c7d2fe" }}]
                }},
                {{
                    "featureType": "water",
                    "elementType": "geometry",
                    "stylers": [{{ "color": "#93c5fd" }}]
                }}
            ]
        }});

        const routePath = new google.maps.Polyline({{
            path: [
                {",".join([f"{{ lat: {lat}, lng: {lng} }}" for lng, lat in path])}
            ],
            geodesic: true,
            strokeColor: "#10b981",
            strokeOpacity: 1.0,
            strokeWeight: 5,
        }});

        routePath.setMap(map);

        new google.maps.Marker({{
            position: start,
            map,
            title: "출발지",
            icon: {{
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: "#2563eb",
                fillOpacity: 1,
                strokeColor: "#1e3a8a",
                strokeWeight: 2
            }}
        }});

        new google.maps.Marker({{
            position: end,
            map,
            title: "도착지",
            icon: {{
                path: google.maps.SymbolPath.CIRCLE,
                scale: 8,
                fillColor: "#ef4444",
                fillOpacity: 1,
                strokeColor: "#991b1b",
                strokeWeight: 2
            }}
        }});
    }}
    </script>

    <script async
    src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap">
    </script>
    """

    st.components.v1.html(google_map_html, height=530)

    st.markdown("</div>", unsafe_allow_html=True)
