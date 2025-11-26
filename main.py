import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# ------------------------------------------
# 기본 설정
# ------------------------------------------
st.set_page_config(page_title="골든 타임", layout="wide")

# 하나고 위치
DEFAULT_LAT = 37.641240416205285
DEFAULT_LON = 126.93756984090838

HOTLINE = "010-9053-0540"

# ------------------------------------------
# 전역 스타일 (디자인 고급화)
# ------------------------------------------
st.markdown(
    """
    <style>
    .main {
        background: linear-gradient(135deg, #f3f7ff 0%, #ffffff 60%);
    }
    .app-title {
        font-size: 40px;
        font-weight: 800;
        color: #1f2933;
        margin-bottom: 8px;
    }
    .app-subtitle {
        font-size: 18px;
        color: #5f6c80;
        margin-bottom: 0;
    }
    .card {
        background: white;
        padding: 24px 28px;
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
        margin-bottom: 18px;
        border: 1px solid #e5e9f2;
    }
    .card-header {
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 8px;
        color: #1f2933;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .step-badge {
        display:inline-block;
        background:#2563eb;
        color:white;
        font-size:12px;
        padding:2px 8px;
        border-radius:999px;
        margin-right:6px;
    }
    .stButton>button {
        border-radius: 999px;
        font-size: 18px;
        padding: 12px 24px;
        border: none;
        box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3);
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
    .pill {
        display:inline-block;
        padding:4px 10px;
        border-radius:999px;
        background:#e5edff;
        color:#334e68;
        font-size:12px;
        margin-bottom:6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------
# 병명 리스트
# ------------------------------------------
DISEASES = [
    "심근경색",
    "뇌출혈",
    "뇌진탕",
    "심장마비",
    "뇌졸중",
    "발작",
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
        "treats_default": with_defaults(
            {"뇌진탕": True, "뇌졸중": True, "발작": True}
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
    "성누가병원": {
        "lat": 37.6099,
        "lon": 126.9293,
        "address": "서울특별시 은평구 281-102",
        "phone": "1660-0075",
        "website": "https://slmc.co.kr/new/index.php",
        "treats_default": with_defaults(
            {"뇌출혈": True, "뇌진탕": True, "뇌졸중": True, "아나필락시스": True}
        ),
    }, 
    "서울 특별시 은평병원": {
        "lat": 37.5940039,
        "lon": 126.9232331,
        "address": "서울특별시 은평구 백련산로 90",
        "phone": "02-444-5555",
        "website": "http://epmhc.or.kr",
        "treats_default": with_defaults(
            {"뇌출혈": True, "뇌진탕": True, "뇌졸중": True, "발작": True}
        ),
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "address": "서울특별시 은평구 은평로 133",
        "phone": "02-666-7777",
        "website": "http://seobuhospital.co.kr",
        "treats_default": with_defaults(
            {"심근경색": True, "뇌진탕": True, "발작": True}
        ),
    },
    "청구 성심 병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "address": "서울특별시 은평구 통일로 873",
        "phone": "02-777-8888",
        "website": "http://www.chunggu.co.kr",
        "treats_default": with_defaults(
            {
                "심근경색": True,
                "뇌출혈": True,
                "뇌졸중": True,
                "패혈증": True,
                "발작": True,
            }
        ),
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
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


# ------------------------------------------
# OSRM 최단 경로 계산 (도로 기준)
# ------------------------------------------
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
# 세션 상태 초기화
# ------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }

# ==========================================================
#                    HOME 화면
# ==========================================================
if st.session_state.page == "home":
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown(
            """
            <div class="card" style="text-align:center;margin-top:80px;">
                <div class="app-title">⏱ 골든 타임</div>
                <p class="app-subtitle">은평권 응급 환자 이송 · 병원 매칭 시스템</p>
                <div style="margin-top:16px;">
                    <span class="pill">하나고 출발 기준</span>
                    <span class="pill">실제 도로 기준 최적 경로</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container():
            c1, c2 = st.columns(2)
            with c1:
                with st.container():
                    st.markdown('<div class="mode-btn-hospital">', unsafe_allow_html=True)
                    if st.button("🏥 병원 모드", use_container_width=True):
                        st.session_state.page = "hospital"
                    st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                with st.container():
                    st.markdown('<div class="mode-btn-ambulance">', unsafe_allow_html=True)
                    if st.button("🚑 구급차 모드", use_container_width=True):
                        st.session_state.page = "ambulance"
                    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
#                    병원 모드
# ==========================================================
elif st.session_state.page == "hospital":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.markdown(
            '<div class="card-header">🏥 병원 모드</div>', unsafe_allow_html=True
        )
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # 카드 1: 병원 선택 + 체크리스트
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-header"><span class="step-badge">STEP 1</span>병원 선택 및 수용 가능 질환 설정</div>',
        unsafe_allow_html=True,
    )
    hospital = st.selectbox("병원을 선택하세요.", list(HOSPITALS.keys()))
    info = HOSPITALS[hospital]

    st.write("치료 가능한 병명을 체크해 주세요:")
    cols = st.columns(2)
    for idx, d in enumerate(DISEASES):
        with cols[idx % 2]:
            st.session_state.hospital_treats[hospital][d] = st.checkbox(
                d, value=st.session_state.hospital_treats[hospital][d], key=f"{hospital}_{d}"
            )
    st.markdown("</div>", unsafe_allow_html=True)

    # 카드 2: 병원 정보 + 지도
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-header"><span class="step-badge">STEP 2</span>병원 정보</div>',
        unsafe_allow_html=True,
    )
    st.write(f"**병원명** : {hospital}")
    st.write(f"**주소** : {info['address']}")

    st.markdown(
        f"""
        <a href="tel:{info['phone']}">
            <button style="padding:10px 20px;background:#2563EB;color:white;
                           border:none;border-radius:999px;font-size:16px;margin-top:6px;">
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
        get_color=[239, 68, 68],  # 빨강
        get_radius=260,
    )

    view = pdk.ViewState(latitude=info["lat"], longitude=info["lon"], zoom=14)

    st.pydeck_chart(pdk.Deck(layers=[hospital_layer], initial_view_state=view))
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================
#                    구급차 모드
# ==========================================================
elif st.session_state.page == "ambulance":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.markdown(
            '<div class="card-header">🚑 구급차 모드</div>', unsafe_allow_html=True
        )
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # 카드 1: 내 위치 안내 + 병명 선택
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-header"><span class="step-badge">STEP 1</span>병명 선택</div>',
        unsafe_allow_html=True,
    )

    st.write("📍 현재 출발지: **하나고등학교 (은평구 연서로 535)**")
    disease = st.radio("환자의 병명을 선택하세요.", DISEASES, horizontal=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 치료 가능 병원 필터링
    candidates = []
    for h, i in HOSPITALS.items():
        if st.session_state.hospital_treats[h][disease]:
            dist, eta, _ = get_route_osrm(DEFAULT_LAT, DEFAULT_LON, i["lat"], i["lon"])
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

    # 카드 2: 병원 선택 테이블
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-header"><span class="step-badge">STEP 2</span>수용 가능 병원 선택</div>',
        unsafe_allow_html=True,
    )

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
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.MODEL_CHANGED,
        height=260,
        theme="balham",
    )

    raw_sel = grid.get("selected_rows", [])

    # selected_rows → list[dict]로 정규화
    if isinstance(raw_sel, pd.DataFrame):
        selected_rows = raw_sel.to_dict("records")
    elif isinstance(raw_sel, list):
        selected_rows = raw_sel
    else:
        selected_rows = []

    if len(selected_rows) > 0:
        selected_name = selected_rows[0]["병원"]
    else:
        selected_name = df.iloc[0]["병원"]

    sel = df[df["병원"] == selected_name].iloc[0]

    st.markdown(
        f"**선택된 병원:** `{selected_name}` · 거리 약 **{sel['거리(km)']} km**, "
        f"예상 **{sel['도착예상(분)']} 분**",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # 카드 3: 연락 수단
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-header"><span class="step-badge">STEP 3</span>연락 및 핫라인</div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"📍 **주소** : {sel['address']}")
        st.markdown(
            f"""
            <a href="tel:{sel['phone']}">
                <button style="padding:10px 20px;background:#2563EB;color:white;
                               border:none;border-radius:999px;font-size:16px;">
                    📞 {sel['phone']} 병원으로 전화하기
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <a href="{sel['website']}" target="_blank">
                <button style="margin-top:8px;padding:10px 20px;background:#4B5563;color:white;
                               border:none;border-radius:999px;font-size:16px;">
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
                <button style="padding:12px 24px;background:#DC2626;color:white;
                               border:none;border-radius:999px;font-size:18px;">
                    🚨 {HOTLINE} 으로 즉시 전화
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # 카드 4: 지도 + 네이버 길찾기
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="card-header"><span class="step-badge">STEP 4</span>지도 및 길안내</div>',
        unsafe_allow_html=True,
    )

    dist, eta, path = get_route_osrm(
        DEFAULT_LAT, DEFAULT_LON, sel["lat"], sel["lon"]
    )

    st.write(
        f"🛣 도로 기준 거리: **{round(dist,2)} km**, 예상 소요 시간: **{round(eta,1)} 분**"
    )

    ambulance_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": DEFAULT_LAT, "lon": DEFAULT_LON}],
        get_position="[lon, lat]",
        get_radius=320,
        get_color=[37, 99, 235],  # 파랑
    )

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": sel["lat"], "lon": sel["lon"]}],
        get_position="[lon, lat]",
        get_radius=340,
        get_color=[239, 68, 68],  # 빨강
    )

    path_layer = pdk.Layer(
        "PathLayer",
        data=[{"path": path}],
        get_path="path",
        get_width=6,
        get_color=[16, 185, 129],  # 초록
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[ambulance_layer, hospital_layer, path_layer],
            initial_view_state=pdk.ViewState(
                latitude=(DEFAULT_LAT + sel["lat"]) / 2,
                longitude=(DEFAULT_LON + sel["lon"]) / 2,
                zoom=13,
            ),
            tooltip={"text": "응급 이송 경로"},
        )
    )

    # 네이버 지도 길찾기 (앱용 nmap://)
    nmap_url = (
        "nmap://route/car?"
        f"slat={DEFAULT_LAT}&slng={DEFAULT_LON}&sname=하나고등학교&"
        f"dlat={sel['lat']}&dlng={sel['lon']}&dname={selected_name}&"
        "appname=goldentime"
    )

    # 웹 브라우저용 네이버 지도 (fallback)
    web_url = (
        "https://map.naver.com/v5/directions/-/-/"
        f"{DEFAULT_LON},{DEFAULT_LAT}/{sel['lon']},{sel['lat']}/0?c=14,0,0,0,dh"
    )

    st.markdown(
        f"""
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;">
            <a href="{nmap_url}">
                <button style="padding:10px 20px;background:#03C75A;color:white;
                               border:none;border-radius:999px;font-size:16px;">
                    🧭 네이버 지도 앱으로 길찾기
                </button>
            </a>
            <a href="{web_url}" target="_blank">
                <button style="padding:10px 20px;background:#111827;color:white;
                               border:none;border-radius:999px;font-size:16px;">
                    🌐 브라우저에서 네이버 지도 열기
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
