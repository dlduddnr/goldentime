import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# folium & streamlit-folium 안전 import
try:
    import folium
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except:
    FOLIUM_AVAILABLE = False

# GPS
try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_AVAILABLE = True
except:
    GEO_AVAILABLE = False


# -------------------------------------------------------
# 기본 Streamlit 설정
# -------------------------------------------------------
st.set_page_config(page_title="골든 타임", layout="wide")

DEFAULT_LAT = 37.641240416205285
DEFAULT_LON = 126.93756984090838
HOTLINE = "010-9053-0540"


# -------------------------------------------------------
# 다국어 시스템
# -------------------------------------------------------
TEXT = {
    "ko": {
        "app_title": "⏱ 골든 타임",
        "app_subtitle": "은평권 응급 환자 이송 · 병원 매칭 시스템",
        "lang_label": "언어 선택",
        "mode_hospital": "🏥 병원 모드",
        "mode_ambulance": "🚑 구급차 모드",
        "back_home": "⬅ 홈으로 이동",
        "hospital_title": "🏥 병원 모드",
        "hospital_step1": "1. 병원 선택 및 진료 가능 질환 체크",
        "hospital_step2": "2. 병원 정보",
        "hospital_select": "병원 선택",
        "hospital_check_desc": "이 병원이 치료 가능한 질환을 체크하세요:",
        "hospital_call_btn": "📞 병원 대표번호 전화",
        "hospital_map": "병원 위치",
        "ambulance_title": "🚑 구급차 모드",
        "amb_step1": "1. 출발 위치 선택",
        "amb_step2": "2. 병명 선택",
        "amb_step3": "3. 치료 가능한 병원 선택",
        "amb_step4": "4. 연락 / 핫라인",
        "amb_step5": "5. 지도 및 길안내",
        "disease_prompt": "환자의 상태(병명)를 선택하세요:",
        "no_hospital": "🚫 이 병명을 치료 가능한 병원이 없습니다.",
        "selected_hospital": "선택된 병원",
        "hotline_title": "응급 핫라인",
        "addr": "주소",
        "distance_eta": "거리: {dist} km / 예상: {eta} 분",
        "start_from": "출발지: {name}",
        "map_click_hint": "🖱 지도를 클릭하면 출발지 후보가 표시됩니다.",
        "map_click_selected": "클릭한 위치: 위도 {lat}, 경도 {lon}",
        "map_click_set_button": "이 위치를 출발지로 설정",
        "nav_app_btn": "🧭 네이버 지도 앱에서 길찾기",
        "nav_web_btn": "🌐 네이버 지도 웹 열기",
    },
    "en": {
        "app_title": "⏱ Golden Time",
        "app_subtitle": "Eunpyeong Emergency Transport System",
        "lang_label": "Language",
        "mode_hospital": "🏥 Hospital Mode",
        "mode_ambulance": "🚑 Ambulance Mode",
        "back_home": "⬅ Back to Home",
        "hospital_title": "🏥 Hospital Mode",
        "hospital_step1": "1. Select hospital & diseases",
        "hospital_step2": "2. Hospital information",
        "hospital_select": "Select hospital",
        "hospital_check_desc": "Select treatable diseases:",
        "hospital_call_btn": "📞 Call Hospital",
        "hospital_map": "Location",
        "ambulance_title": "🚑 Ambulance Mode",
        "amb_step1": "1. Select starting point",
        "amb_step2": "2. Select disease",
        "amb_step3": "3. Choose available hospital",
        "amb_step4": "4. Contact / Hotline",
        "amb_step5": "5. Map & Navigation",
        "disease_prompt": "Select disease:",
        "no_hospital": "🚫 No hospital can currently treat this disease.",
        "selected_hospital": "Selected hospital",
        "hotline_title": "Emergency hotline",
        "addr": "Address",
        "distance_eta": "Distance: {dist} km / ETA: {eta} min",
        "start_from": "Start from: {name}",
        "map_click_hint": "🖱 Click the map to select a starting point.",
        "map_click_selected": "Clicked: lat {lat}, lon {lon}",
        "map_click_set_button": "Set as start point",
        "nav_app_btn": "🧭 Navigate in Naver App",
        "nav_web_btn": "🌐 Open Naver Maps Web",
    },
}

def T(key):
    return TEXT[st.session_state.get("lang", "ko")].get(key, key)


# -------------------------------------------------------
# 병명 목록
# -------------------------------------------------------
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


# -------------------------------------------------------
# 병원 데이터
# -------------------------------------------------------
def treats(**kwargs):
    base = {d: False for d in DISEASES}
    base.update(kwargs)
    return base

HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160, "lon": 126.9170,
        "address": "은평구 연서로 177",
        "phone": "02-111-2222",
        "treats": treats(뇌진탕=True, 뇌졸중=True),
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370, "lon": 126.9190,
        "address": "은평구 통일로 1021",
        "phone": "02-222-3333",
        "treats": treats(심근경색=True, 뇌출혈=True, 뇌졸중=True),
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940, "lon": 126.9232,
        "address": "은평구 백련산로 90",
        "phone": "02-444-5555",
        "treats": treats(뇌출혈=True, 뇌진탕=True),
    },
    "본 서부병원": {
        "lat": 37.6050, "lon": 126.9090,
        "address": "은평구 은평로 133",
        "phone": "02-666-7777",
        "treats": treats(심근경색=True),
    },
    "청구 성심 병원": {
        "lat": 37.6290, "lon": 126.9220,
        "address": "은평구 통일로 873",
        "phone": "02-777-8888",
        "treats": treats(심근경색=True, 뇌졸중=True),
    },
    "성누가병원": {
        "lat": 37.6099, "lon": 126.9293,
        "address": "은평구 281-102",
        "phone": "02-888-9999",
        "treats": treats(심근경색=True, 뇌출혈=True),
    },
    "리드힐병원": {
        "lat": 37.6203, "lon": 126.9299,
        "address": "은평구 연서로 10",
        "phone": "02-555-6666",
        "treats": treats(심근경색=True, 기흉=True),
    },
    "연세노블병원": {
        "lat": 37.6018, "lon": 126.9270,
        "address": "은평구 녹번동 154-19",
        "phone": "02-999-0000",
        "treats": treats(뇌졸중=True, 뇌수막염=True),
    },
}


# -------------------------------------------------------
# 거리 및 OSRM 경로 계산
# -------------------------------------------------------
def haversine(a_lat, a_lon, b_lat, b_lon):
    R = 6371
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(a_lat)) *
         math.cos(math.radians(b_lat)) *
         math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))

def get_route(start_lat, start_lon, end_lat, end_lon):
    url = f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        route = r["routes"][0]
        dist = route["distance"] / 1000
        eta = route["duration"] / 60
        coords = [(c[1], c[0]) for c in route["geometry"]["coordinates"]]
        return dist, eta, coords
    except:
        d = haversine(start_lat, start_lon, end_lat, end_lon)
        return d, d / 50 * 60, [(start_lat, start_lon), (end_lat, end_lon)]


# -------------------------------------------------------
# 세션 초기화
# -------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "ko"

if "page" not in st.session_state:
    st.session_state.page = "home"

if "start_lat" not in st.session_state:
    st.session_state.start_lat = DEFAULT_LAT
    st.session_state.start_lon = DEFAULT_LON
    st.session_state.start_name = "하나고등학교"

if "candidate_lat" not in st.session_state:
    st.session_state.candidate_lat = None
if "candidate_lon" not in st.session_state:
    st.session_state.candidate_lon = None


# -------------------------------------------------------
# 홈 화면
# -------------------------------------------------------
if st.session_state.page == "home":
    st.title(T("app_title"))
    st.caption(T("app_subtitle"))

    st.session_state.lang = st.radio(
        T("lang_label"), ["ko", "en"], horizontal=True,
        format_func=lambda x: "한국어" if x == "ko" else "English"
    )

    st.write("")
    if st.button(T("mode_hospital")):
        st.session_state.page = "hospital"

    if st.button(T("mode_ambulance")):
        st.session_state.page = "ambulance"


# -------------------------------------------------------
# 병원 모드
# -------------------------------------------------------
elif st.session_state.page == "hospital":
    if st.button(T("back_home")):
        st.session_state.page = "home"

    st.header(T("hospital_title"))
    st.subheader(T("hospital_step1"))

    hospital = st.selectbox(T("hospital_select"), list(HOSPITALS.keys()))
    info = HOSPITALS[hospital]

    st.write(T("hospital_check_desc"))
    cols = st.columns(2)
    for i, d in enumerate(DISEASES):
        with cols[i % 2]:
            info["treats"][d] = st.checkbox(d, value=info["treats"][d])

    st.subheader(T("hospital_step2"))
    st.write(f"📍 {info['address']}")

    st.markdown(f"""
        <a href="tel:{info['phone']}">
            <button style="padding:10px;background:#2563EB;color:white;border-radius:10px;">
                {T('hospital_call_btn')}
            </button>
        </a>
    """, unsafe_allow_html=True)

    marker = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": info["lat"], "lon": info["lon"]}],
        get_position='[lon, lat]', get_color=[255, 0, 0], get_radius=200
    )
    st.pydeck_chart(pdk.Deck(
        layers=[marker],
        initial_view_state=pdk.ViewState(latitude=info["lat"], longitude=info["lon"], zoom=14)
    ))


# -------------------------------------------------------
# 구급차 모드
# -------------------------------------------------------
elif st.session_state.page == "ambulance":

    if st.button(T("back_home")):
        st.session_state.page = "home"

    st.header(T("ambulance_title"))

    # STEP1: 출발 위치
    st.subheader(T("amb_step1"))
    st.write(f"현재 출발지: **{st.session_state.start_name}**")

    if GEO_AVAILABLE and st.button("📡 GPS"):
        loc = streamlit_geolocation()
        if loc and loc.get("latitude"):
            st.session_state.start_lat = loc["latitude"]
            st.session_state.start_lon = loc["longitude"]
            st.session_state.start_name = "현재 위치"
            st.success("GPS 위치 설정 완료.")

    # STEP2
    st.subheader(T("amb_step2"))
    disease = st.radio(T("disease_prompt"), DISEASES, horizontal=True)

    # STEP3
    st.subheader(T("amb_step3"))
    candidates = []
    for h, info in HOSPITALS.items():
        if info["treats"].get(disease, False):
            dist, eta, _ = get_route(
                st.session_state.start_lat,
                st.session_state.start_lon,
                info["lat"], info["lon"]
            )
            candidates.append({
                "병원": h, "거리(km)": round(dist, 2),
                "도착(분)": round(eta, 1),
                "address": info["address"],
                "phone": info["phone"],
                "lat": info["lat"], "lon": info["lon"],
            })

    df = pd.DataFrame(candidates)

    if df.empty:
        st.error(T("no_hospital"))
        st.stop()

    df = df.sort_values("도착(분)")

    gob = GridOptionsBuilder.from_dataframe(df)
    gob.configure_selection("single")
    grid = AgGrid(df, update_mode=GridUpdateMode.SELECTION_CHANGED)

    selected = grid.get("selected_rows", [])
    if selected:
        sel_row = selected[0]
    else:
        sel_row = df.iloc[0]

    st.write(f"**{T('selected_hospital')}:** {sel_row['병원']}")

    # STEP4
    st.subheader(T("amb_step4"))
    st.write(f"{T('addr')}: {sel_row['address']}")

    st.markdown(f"""
        <a href="tel:{sel_row['phone']}">
            <button style="padding:10px;background:#2563EB;color:white;border-radius:10px;">
                📞 {sel_row['phone']}
            </button>
        </a>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <a href="tel:{HOTLINE}">
            <button style="padding:10px;background:#DC2626;color:white;border-radius:10px;">
                🚨 {HOTLINE}
            </button>
        </a>
    """, unsafe_allow_html=True)

    # STEP5
    st.subheader(T("amb_step5"))

    dist, eta, route = get_route(
        st.session_state.start_lat, st.session_state.start_lon,
        sel_row["lat"], sel_row["lon"]
    )
    st.write(T("distance_eta").format(dist=dist, eta=eta))

    if not FOLIUM_AVAILABLE:
        st.error("⚠ folium 모듈이 설치되지 않아 지도 기능을 사용할 수 없습니다.")
        st.stop()

    # 지도 중심
    center_lat = (st.session_state.start_lat + sel_row["lat"]) / 2
    center_lon = (st.session_state.start_lon + sel_row["lon"]) / 2

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # 출발지
    folium.Marker(
        [st.session_state.start_lat, st.session_state.start_lon],
        tooltip="출발지"
    ).add_to(fmap)

    # 병원
    folium.Marker(
        [sel_row["lat"], sel_row["lon"]],
        tooltip=sel_row["병원"], icon=folium.Icon(color="red")
    ).add_to(fmap)

    # 경로
    folium.PolyLine(route, color="blue", weight=5).add_to(fmap)

    # 후보 위치
    md = st_folium(fmap, height=400)
    if md and md.get("last_clicked"):
        st.session_state.candidate_lat = md["last_clicked"]["lat"]
        st.session_state.candidate_lon = md["last_clicked"]["lng"]

    if st.session_state.candidate_lat:
        st.info(T("map_click_selected").format(
            lat=st.session_state.candidate_lat,
            lon=st.session_state.candidate_lon
        ))
        if st.button(T("map_click_set_button")):
            st.session_state.start_lat = st.session_state.candidate_lat
            st.session_state.start_lon = st.session_state.candidate_lon
            st.session_state.start_name = "지도 선택 위치"
            st.success("출발지가 변경되었습니다.")

    # 네이버 길찾기
    nmap_url = (
        f"nmap://route/car?"
        f"slat={st.session_state.start_lat}&slng={st.session_state.start_lon}"
        f"&sname=start&dlat={sel_row['lat']}&dlng={sel_row['lon']}"
        f"&dname={sel_row['병원']}&appname=goldentime"
    )

    web_url = (
        f"https://map.naver.com/v5/directions/-/-/"
        f"{st.session_state.start_lon},{st.session_state.start_lat}/"
        f"{sel_row['lon']},{sel_row['lat']}/0?c=14,0,0,0,dh"
    )

    st.markdown(f"""
        <a href="{nmap_url}">
            <button style="padding:10px;background:#03C75A;color:white;border-radius:10px;margin-top:8px;">
                {T('nav_app_btn')}
            </button>
        </a>
        <a href="{web_url}" target="_blank">
            <button style="padding:10px;background:#111827;color:white;border-radius:10px;margin-left:10px;">
                {T('nav_web_btn')}
            </button>
        </a>
    """, unsafe_allow_html=True)
