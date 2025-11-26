import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# folium + streamlit-folium : 지도 클릭용
import folium
from streamlit_folium import st_folium

# GPS (없어도 앱은 돌아가게 예외 처리)
try:
    from streamlit_geolocation import streamlit_geolocation
    GEO_AVAILABLE = True
except ImportError:
    GEO_AVAILABLE = False

# ------------------------------------------
# 기본 설정
# ------------------------------------------
st.set_page_config(page_title="골든 타임", layout="wide")

# 하나고 기본 출발 위치
DEFAULT_LAT = 37.641240416205285
DEFAULT_LON = 126.93756984090838
DEFAULT_START_NAME_KO = "하나고등학교"
DEFAULT_START_NAME_EN = "Hana High School"

HOTLINE = "010-9053-0540"

# ------------------------------------------
# 다국어 텍스트
# ------------------------------------------
TEXT = {
    "ko": {
        "app_title": "⏱ 골든 타임",
        "app_subtitle": "은평권 응급 환자 이송 · 병원 매칭 시스템",
        "lang_label": "언어 선택 / Language",
        "mode_hospital": "🏥 병원 모드",
        "mode_ambulance": "🚑 구급차 모드",
        "home_hint": "사용할 모드를 선택해 주세요.",
        "back_home": "⬅ 홈으로",
        "hospital_title": "🏥 병원 모드",
        "hospital_step1": "1. 병원 선택 및 수용 가능 병명 설정",
        "hospital_step2": "2. 병원 정보",
        "hospital_select": "병원을 선택하세요.",
        "hospital_check_desc": "치료 가능한 병명을 체크해 주세요:",
        "hospital_name": "병원명",
        "hospital_addr": "주소",
        "hospital_call_btn": "📞 대표번호로 전화하기",
        "hospital_map": "위치 지도",
        "ambulance_title": "🚑 구급차 모드",
        "amb_step1": "1. 출발 위치 선택",
        "amb_step2": "2. 병명 선택",
        "amb_step3": "3. 수용 가능 병원 선택",
        "amb_step4": "4. 연락 및 핫라인",
        "amb_step5": "5. 지도 및 길안내",
        "default_start": "기본 출발지",
        "gps_info": "📡 GPS 버튼을 누르면 현재 기기 위치를 사용합니다.",
        "gps_button": "📍 GPS로 현재 위치 가져오기",
        "gps_not_available": "⚠ GPS 기능을 사용하려면 `streamlit-geolocation` 패키지가 필요합니다.",
        "disease_prompt": "환자의 병명을 선택하세요.",
        "no_hospital": "🚫 해당 병명을 치료 가능한 병원이 없습니다.",
        "no_hospital_row": "병원 없음",
        "selected_hospital": "선택된 병원",
        "addr": "주소",
        "hotline_title": "응급 핫라인",
        "distance_eta": "도로 기준 거리: {dist} km, 예상 소요 시간: {eta} 분",
        "start_from": "출발지: {name}",
        "nav_app_btn": "🧭 네이버 지도 앱으로 길찾기",
        "nav_web_btn": "🌐 브라우저에서 네이버 지도 열기",
        "map_click_hint": "🖱 지도 위를 클릭하면 '후보 출발지'가 표시됩니다.",
        "map_click_selected": "선택된 후보 위치: 위도 {lat}, 경도 {lon}",
        "map_click_set_button": "✅ 이 위치를 출발지로 설정",
    },
    "en": {
        "app_title": "⏱ Golden Time",
        "app_subtitle": "Emergency Transport & Hospital Matching System",
        "lang_label": "Language / 언어 선택",
        "mode_hospital": "🏥 Hospital Mode",
        "mode_ambulance": "🚑 Ambulance Mode",
        "home_hint": "Please choose a mode.",
        "back_home": "⬅ Back to Home",
        "hospital_title": "🏥 Hospital Mode",
        "hospital_step1": "1. Select hospital & set available diseases",
        "hospital_step2": "2. Hospital information",
        "hospital_select": "Select a hospital",
        "hospital_check_desc": "Check the diseases this hospital can treat:",
        "hospital_name": "Hospital",
        "hospital_addr": "Address",
        "hospital_call_btn": "📞 Call main phone",
        "hospital_map": "Location",
        "ambulance_title": "🚑 Ambulance Mode",
        "amb_step1": "1. Choose starting point",
        "amb_step2": "2. Select disease",
        "amb_step3": "3. Select available hospital",
        "amb_step4": "4. Contact & hotline",
        "amb_step5": "5. Map & navigation",
        "default_start": "Default start",
        "gps_info": "📡 GPS can get your real current location.",
        "gps_button": "📍 Use GPS location",
        "gps_not_available": "⚠ Install `streamlit-geolocation` for GPS.",
        "disease_prompt": "Select the disease:",
        "no_hospital": "🚫 No hospital can treat this disease.",
        "no_hospital_row": "No hospital",
        "selected_hospital": "Selected hospital",
        "addr": "Address",
        "hotline_title": "Emergency hotline",
        "distance_eta": "Road distance: {dist} km, ETA: {eta} min",
        "start_from": "Start: {name}",
        "nav_app_btn": "🧭 Navigate in Naver Map app",
        "nav_web_btn": "🌐 Open in Naver Map (web)",
        "map_click_hint": "🖱 Click the map to choose a start candidate.",
        "map_click_selected": "Selected candidate: lat {lat}, lon {lon}",
        "map_click_set_button": "✅ Use this as start",
    },
}

def T(key):
    lang = st.session_state.get("lang", "ko")
    return TEXT.get(lang, TEXT["ko"]).get(key, key)

# ------------------------------------------
# 병명 리스트 (발작 제거)
# ------------------------------------------
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

def with_defaults(base):
    t = empty_treats()
    t.update(base)
    return t

# ------------------------------------------
# 병원 데이터
# ------------------------------------------
HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160, "lon": 126.9170,
        "address": "서울 은평구 연서로 177",
        "phone": "02-111-2222",
        "website": "",
        "treats_default": with_defaults({"뇌진탕": True, "뇌졸중": True}),
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370, "lon": 126.9190,
        "address": "서울 은평구 통일로 1021",
        "phone": "02-222-3333",
        "website": "",
        "treats_default": with_defaults({"심근경색": True, "뇌출혈": True, "뇌졸중": True}),
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940, "lon": 126.9232,
        "address": "서울 은평구 백련산로 90",
        "phone": "02-444-5555",
        "website": "",
        "treats_default": with_defaults({"뇌출혈": True, "뇌진탕": True}),
    },
    "본 서부병원": {
        "lat": 37.6050, "lon": 126.9090,
        "address": "서울 은평구 은평로 133",
        "phone": "02-666-7777",
        "website": "",
        "treats_default": with_defaults({"심근경색": True}),
    },
    "청구 성심 병원": {
        "lat": 37.6290, "lon": 126.9220,
        "address": "서울 은평구 통일로 873",
        "phone": "02-777-8888",
        "website": "",
        "treats_default": with_defaults({"심근경색": True, "뇌졸중": True}),
    },
    "성누가병원": {
        "lat": 37.6099, "lon": 126.9293,
        "address": "서울 은평구 281 102번지",
        "phone": "02-888-9999",
        "website": "",
        "treats_default": with_defaults({"심근경색": True, "뇌출혈": True}),
    },
    "리드힐병원": {
        "lat": 37.6203, "lon": 126.9299,
        "address": "서울 은평구 연서로 10",
        "phone": "02-555-6666",
        "website": "",
        "treats_default": with_defaults({"심근경색": True, "기흉": True}),
    },
    "연세노블병원": {
        "lat": 37.6018, "lon": 126.9270,
        "address": "서울 은평구 녹번동 154-19",
        "phone": "02-999-0000",
        "website": "",
        "treats_default": with_defaults({"뇌졸중": True, "뇌수막염": True}),
    },
}

# ------------------------------------------
# 거리 / 경로 계산
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

def get_route_osrm(lat1, lon1, lat2, lon2):
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        route = r["routes"][0]
        coords = route["geometry"]["coordinates"]
        dist = route["distance"] / 1000
        eta = route["duration"] / 60
        path = [[c[0], c[1]] for c in coords]
        return dist, eta, path
    except:
        d = haversine(lat1, lon1, lat2, lon2)
        return d, d / 50 * 60, [[lon1, lat1], [lon2, lat2]]

# ------------------------------------------
# 세션 초기화
# ------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "ko"

if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }

if "start_lat" not in st.session_state:
    st.session_state.start_lat = DEFAULT_LAT
    st.session_state.start_lon = DEFAULT_LON
    st.session_state.start_name_ko = DEFAULT_START_NAME_KO
    st.session_state.start_name_en = DEFAULT_START_NAME_EN

if "candidate_lat" not in st.session_state:
    st.session_state.candidate_lat = None
if "candidate_lon" not in st.session_state:
    st.session_state.candidate_lon = None

def current_start_name():
    return st.session_state.start_name_ko if st.session_state.lang == "ko" else st.session_state.start_name_en

# ==========================================================
#                    HOME 화면
# ==========================================================
if st.session_state.page == "home":
    st.title(T("app_title"))
    st.subheader(T("app_subtitle"))

    st.session_state.lang = st.radio(
        T("lang_label"),
        ["ko", "en"],
        format_func=lambda x: "한국어" if x == "ko" else "English",
        horizontal=True,
    )

    st.write("")
    st.write(T("home_hint"))

    if st.button(T("mode_hospital")):
        st.session_state.page = "hospital"

    if st.button(T("mode_ambulance")):
        st.session_state.page = "ambulance"

# ==========================================================
#                    병원 모드
# ==========================================================
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
            cur = st.session_state.hospital_treats[hospital][d]
            new = st.checkbox(d, value=cur, key=f"{hospital}-{d}")
            st.session_state.hospital_treats[hospital][d] = new

    st.subheader(T("hospital_step2"))
    st.write(f"**{T('hospital_name')}:** {hospital}")
    st.write(f"**{T('hospital_addr')}:** {info['address']}")

    st.markdown(f"""
        <a href="tel:{info['phone']}">
        <button style="padding:10px;border-radius:10px;background:#2563EB;color:white;">
            {T("hospital_call_btn")} ({info['phone']})
        </button></a>
    """, unsafe_allow_html=True)

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": info["lat"], "lon": info["lon"]}],
        get_position='[lon, lat]', get_radius=260,
        get_color=[239, 68, 68]
    )
    st.pydeck_chart(pdk.Deck(
        layers=[hospital_layer],
        initial_view_state=pdk.ViewState(latitude=info["lat"], longitude=info["lon"], zoom=14)
    ))

# ==========================================================
#                    구급차 모드
# ==========================================================
elif st.session_state.page == "ambulance":
    if st.button(T("back_home")):
        st.session_state.page = "home"

    st.header(T("ambulance_title"))

    # STEP1
    st.subheader(T("amb_step1"))
    st.write(f"{T('default_start')}: {current_start_name()}")

    if GEO_AVAILABLE:
        if st.button(T("gps_button")):
            loc = streamlit_geolocation()
            if loc and loc.get("latitude") and loc.get("longitude"):
                st.session_state.start_lat = loc["latitude"]
                st.session_state.start_lon = loc["longitude"]
                st.session_state.start_name_ko = "현재 위치"
                st.session_state.start_name_en = "Current location"
                st.success("GPS 위치가 설정되었습니다.")
    else:
        st.info(T("gps_not_available"))

    # STEP2
    st.subheader(T("amb_step2"))
    disease = st.radio(T("disease_prompt"), DISEASES, horizontal=True)

    # STEP3
    st.subheader(T("amb_step3"))
    candidates = []
    for h, info in HOSPITALS.items():
        if st.session_state.hospital_treats[h].get(disease, False):
            dist, eta, _ = get_route_osrm(
                st.session_state.start_lat, st.session_state.start_lon,
                info["lat"], info["lon"]
            )
            candidates.append({
                "병원": h, "거리(km)": round(dist, 2),
                "도착예상(분)": round(eta, 1),
                "address": info["address"],
                "phone": info["phone"],
                "website": info["website"],
                "lat": info["lat"],
                "lon": info["lon"],
            })

    df = pd.DataFrame(candidates)
    if df.empty:
        st.error(T("no_hospital"))
        st.stop()

    df = df.sort_values("도착예상(분)").reset_index(drop=True)

    gob = GridOptionsBuilder.from_dataframe(df)
    gob.configure_selection("single", use_checkbox=True)
    grid = AgGrid(
        df, gridOptions=gob.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.MODEL_CHANGED
    )

    selected = grid.get("selected_rows", [])
    if selected:
        selected_name = selected[0]["병원"]
    else:
        selected_name = df.iloc[0]["병원"]

    sel = df[df["병원"] == selected_name].iloc[0]

    st.write(f"**{T('selected_hospital')}:** {selected_name}")

    # STEP4
    st.subheader(T("amb_step4"))
    st.write(f"{T('addr')}: {sel['address']}")
    st.markdown(f"""<a href="tel:{sel['phone']}">
        <button style="padding:10px;border-radius:10px;background:#2563EB;color:white;">📞 {sel['phone']}</button>
    </a>""", unsafe_allow_html=True)

    st.markdown(f"""<a href="tel:{HOTLINE}">
        <button style="margin-top:5px;padding:10px;border-radius:10px;background:#DC2626;color:white;">🚨 {HOTLINE}</button>
    </a>""", unsafe_allow_html=True)

    # STEP5
    st.subheader(T("amb_step5"))
    dist, eta, path = get_route_osrm(
        st.session_state.start_lat, st.session_state.start_lon,
        sel["lat"], sel["lon"]
    )
    st.write(T("distance_eta").format(dist=dist, eta=eta))

    # 지도 중심
    center_lat = (st.session_state.start_lat + sel["lat"]) / 2
    center_lon = (st.session_state.start_lon + sel["lon"]) / 2

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    folium.Marker([st.session_state.start_lat, st.session_state.start_lon],
                  tooltip="출발지").add_to(fmap)
    folium.Marker([sel["lat"], sel["lon"]], tooltip="도착지").add_to(fmap)

    route_latlng = [(p[1], p[0]) for p in path]
    folium.PolyLine(route_latlng, color="blue", weight=5).add_to(fmap)

    map_data = st_folium(fmap, height=400)

    if map_data and map_data.get("last_clicked"):
        st.session_state.candidate_lat = map_data["last_clicked"]["lat"]
        st.session_state.candidate_lon = map_data["last_clicked"]["lng"]

    if st.session_state.candidate_lat:
        st.write(T("map_click_selected").format(
            lat=st.session_state.candidate_lat,
            lon=st.session_state.candidate_lon
        ))
        if st.button(T("map_click_set_button")):
            st.session_state.start_lat = st.session_state.candidate_lat
            st.session_state.start_lon = st.session_state.candidate_lon
            st.success("출발지가 변경되었습니다.")

    # 네이버 지도 URL
    nmap_url = (
        "nmap://route/car?"
        f"slat={st.session_state.start_lat}&slng={st.session_state.start_lon}"
        f"&sname=start&dlat={sel['lat']}&dlng={sel['lon']}"
        f"&dname={selected_name}&appname=goldentime"
    )
    web_url = (
        f"https://map.naver.com/v5/directions/-/-/"
        f"{st.session_state.start_lon},{st.session_state.start_lat}/"
        f"{sel['lon']},{sel['lat']}/0?c=14,0,0,0,dh"
    )

    st.markdown(f"""
        <a href="{nmap_url}">
        <button style="margin-top:10px;padding:10px;border-radius:10px;background:#03C75A;color:white;">
            {T("nav_app_btn")}
        </button></a>
        <a href="{web_url}" target="_blank">
        <button style="margin-top:10px;padding:10px;border-radius:10px;background:#111827;color:white;">
            {T("nav_web_btn")}
        </button></a>
    """, unsafe_allow_html=True)
