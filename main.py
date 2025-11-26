import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as stimport math
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
        "gps_info": "📡 GPS 버튼을 누르면 현재 기기 위치를 사용합니다. (브라우저 위치 권한 필요)",
        "gps_button": "📍 GPS로 현재 위치 가져오기",
        "gps_not_available": "⚠ GPS 기능을 사용하려면 `streamlit-geolocation` 패키지가 필요합니다.",
        "disease_prompt": "환자의 병명을 선택하세요.",
        "no_hospital": "🚫 이 병명을 현재 치료 가능으로 체크한 병원이 없습니다.",
        "no_hospital_row": "병원 없음",
        "selected_hospital": "선택된 병원",
        "addr": "주소",
        "hotline_title": "응급 핫라인",
        "map_title": "지도 및 길안내",
        "distance_eta": "도로 기준 거리: {dist} km, 예상 소요 시간: {eta} 분",
        "start_from": "출발지: {name}",
        "nav_app_btn": "🧭 네이버 지도 앱으로 길찾기",
        "nav_web_btn": "🌐 브라우저에서 네이버 지도 열기",
        "map_click_hint": "🖱 지도 위를 클릭하면 '후보 출발지'가 표시됩니다. 아래 버튼을 눌러 출발지로 확정할 수 있습니다.",
        "map_click_selected": "지도에서 선택한 후보 위치: 위도 {lat}, 경도 {lon}",
        "map_click_set_button": "✅ 이 위치를 출발지로 설정",
    },
    "en": {
        "app_title": "⏱ Golden Time",
        "app_subtitle": "Emergency Transport & Hospital Matching System (Eunpyeong area)",
        "lang_label": "Language / 언어 선택",
        "mode_hospital": "🏥 Hospital Mode",
        "mode_ambulance": "🚑 Ambulance Mode",
        "home_hint": "Please choose a mode.",
        "back_home": "⬅ Back to Home",
        "hospital_title": "🏥 Hospital Mode",
        "hospital_step1": "1. Select hospital & available diseases",
        "hospital_step2": "2. Hospital information",
        "hospital_select": "Select a hospital.",
        "hospital_check_desc": "Check the diseases you can treat:",
        "hospital_name": "Hospital",
        "hospital_addr": "Address",
        "hospital_call_btn": "📞 Call main number",
        "hospital_map": "Location map",
        "ambulance_title": "🚑 Ambulance Mode",
        "amb_step1": "1. Choose starting location",
        "amb_step2": "2. Select disease",
        "amb_step3": "3. Choose available hospital",
        "amb_step4": "4. Contact & hotline",
        "amb_step5": "5. Map & navigation",
        "default_start": "Default start",
        "gps_info": "📡 Use GPS to set current device location. (Browser location permission required)",
        "gps_button": "📍 Use GPS location",
        "gps_not_available": "⚠ To use GPS, install `streamlit-geolocation` package.",
        "disease_prompt": "Select patient’s disease.",
        "no_hospital": "🚫 No hospital is currently marked as available for this disease.",
        "no_hospital_row": "No hospital",
        "selected_hospital": "Selected hospital",
        "addr": "Address",
        "hotline_title": "Emergency hotline",
        "map_title": "Map & navigation",
        "distance_eta": "Road distance: {dist} km, ETA: {eta} min",
        "start_from": "Start from: {name}",
        "nav_app_btn": "🧭 Open route in Naver Map app",
        "nav_web_btn": "🌐 Open route in Naver Map (web)",
        "map_click_hint": "🖱 Click on the map to set a candidate starting point, then confirm it with the button below.",
        "map_click_selected": "Candidate start from map: lat {lat}, lon {lon}",
        "map_click_set_button": "✅ Use this point as start",
    },
}


def T(key: str) -> str:
    lang = st.session_state.get("lang", "ko")
    return TEXT.get(lang, TEXT["ko"]).get(key, TEXT["ko"].get(key, key))


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


def with_defaults(custom_dict):
    base = empty_treats()
    base.update(custom_dict)
    return base


# ------------------------------------------
# 병원 데이터 (추가 병원 포함)
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
        "website": "https://example-snugah.or.kr",
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
# 세션 상태 초기화 + 구조 보정
# ------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "ko"

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
    lang = st.session_state.get("lang", "ko")
    return st.session_state.start_name_ko if lang == "ko" else st.session_state.start_name_en


# ==========================================================
#                    HOME 화면
# ==========================================================
if st.session_state.page == "home":
    # 언어 선택
    col_lang, _, _ = st.columns([1, 1, 1])
    with col_lang:
        lang_choice = st.radio(
            T("lang_label"),
            options=["ko", "en"],
            format_func=lambda x: "한국어" if x == "ko" else "English",
            horizontal=True,
        )
        st.session_state.lang = lang_choice

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        # 타이틀 카드 (pill 문구 제거 버전)
        st.markdown(
            f"""
            <div style="background:white;padding:26px 30px;border-radius:18px;
                 box-shadow:0 8px 24px rgba(15,23,42,0.12);border:1px solid #e5e9f2;
                 text-align:center;">
                <div style="font-size:38px;font-weight:800;color:#111827;margin-bottom:6px;">
                    {T("app_title")}
                </div>
                <p style="font-size:17px;color:#4b5563;margin-bottom:4px;">
                    {T("app_subtitle")}
                </p>
                <p style="margin-top:8px;color:#6b7280;font-size:14px;">
                    {T("home_hint")}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="mode-btn-hospital">', unsafe_allow_html=True)
            if st.button(T("mode_hospital"), use_container_width=True):
                st.session_state.page = "hospital"
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="mode-btn-ambulance">', unsafe_allow_html=True)
            if st.button(T("mode_ambulance"), use_container_width=True):
                st.session_state.page = "ambulance"
            st.markdown("</div>", unsafe_allow_html=True)

# ==========================================================
#                    병원 모드
# ==========================================================
elif st.session_state.page == "hospital":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader(T("hospital_title"))
    with top_right:
        if st.button(T("back_home")):
            st.session_state.page = "home"

    # STEP1
    st.markdown(
        f"<div style='background:white;padding:20px 22px;border-radius:16px;"
        f"box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #e5e9f2;'>"
        f"<div style='font-size:18px;font-weight:700;margin-bottom:8px;'>{T('hospital_step1')}</div>",
        unsafe_allow_html=True,
    )

    hospital = st.selectbox(T("hospital_select"), list(HOSPITALS.keys()))
    info = HOSPITALS[hospital]

    st.write(T("hospital_check_desc"))
    cols = st.columns(2)
    for idx, d in enumerate(DISEASES):
        with cols[idx % 2]:
            current = st.session_state.hospital_treats[hospital].get(d, False)
            new_val = st.checkbox(d, value=current, key=f"{hospital}_{d}")
            st.session_state.hospital_treats[hospital][d] = new_val
    st.markdown("</div>", unsafe_allow_html=True)

    # STEP2
    st.markdown(
        f"<div style='background:white;padding:20px 22px;border-radius:16px;"
        f"box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #e5e9f2;margin-top:14px;'>"
        f"<div style='font-size:18px;font-weight:700;margin-bottom:8px;'>{T('hospital_step2')}</div>",
        unsafe_allow_html=True,
    )

    st.write(f"**{T('hospital_name')}:** {hospital}")
    st.write(f"**{T('hospital_addr')}:** {info['address']}")

    st.markdown(
        f"""
        <a href="tel:{info['phone']}">
            <button style="padding:8px 18px;background:#2563EB;color:white;
                           border:none;border-radius:999px;font-size:15px;margin-top:6px;">
                {T('hospital_call_btn')} ({info['phone']})
            </button>
        </a>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    st.write(f"**{T('hospital_map')}**")

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
#                    구급차 모드
# ==========================================================
elif st.session_state.page == "ambulance":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader(T("ambulance_title"))
    with top_right:
        if st.button(T("back_home")):
            st.session_state.page = "home"

    # STEP1: 출발 위치
    st.markdown(
        f"<div style='background:white;padding:20px 22px;border-radius:16px;"
        f"box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #e5e9f2;'>"
        f"<div style='font-size:18px;font-weight:700;margin-bottom:8px;'>{T('amb_step1')}</div>",
        unsafe_allow_html=True,
    )

    default_name = (
        DEFAULT_START_NAME_KO if st.session_state.lang == "ko" else DEFAULT_START_NAME_EN
    )
    st.write(f"{T('default_start')}: **{default_name}**")

    if GEO_AVAILABLE:
        st.info(T("gps_info"))
        if st.button(T("gps_button")):
            loc = streamlit_geolocation()
            if isinstance(loc, dict) and loc.get("latitude") and loc.get("longitude"):
                st.session_state.start_lat = loc["latitude"]
                st.session_state.start_lon = loc["longitude"]
                if st.session_state.lang == "ko":
                    st.session_state.start_name_ko = "현재 위치"
                    st.session_state.start_name_en = "Current location"
                else:
                    st.session_state.start_name_en = "Current location"
                    st.session_state.start_name_ko = "현재 위치"
                st.success(
                    f"위도 {st.session_state.start_lat:.5f}, 경도 {st.session_state.start_lon:.5f}"
                )
            else:
                st.warning("위치 정보를 가져오지 못했습니다. 기본 위치를 계속 사용합니다.")
    else:
        st.info(T("gps_not_available"))

    st.markdown("</div>", unsafe_allow_html=True)

    # STEP2: 병명 선택
    st.markdown(
        f"<div style='background:white;padding:20px 22px;border-radius:16px;"
        f"box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #e5e9f2;margin-top:14px;'>"
        f"<div style='font-size:18px;font-weight:700;margin-bottom:8px;'>{T('amb_step2')}</div>",
        unsafe_allow_html=True,
    )
    disease = st.radio(T("disease_prompt"), DISEASES, horizontal=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # STEP3: 수용 가능 병원 필터링 + 선택
    st.markdown(
        f"<div style='background:white;padding:20px 22px;border-radius:16px;"
        f"box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #e5e9f2;margin-top:14px;'>"
        f"<div style='font-size:18px;font-weight:700;margin-bottom:8px;'>{T('amb_step3')}</div>",
        unsafe_allow_html=True,
    )

    candidates = []
    for h, i in HOSPITALS.items():
        can_treat = st.session_state.hospital_treats.get(h, {}).get(disease, False)
        if can_treat:
            dist, eta, _ = get_route_osrm(
                st.session_state.start_lat, st.session_state.start_lon, i["lat"], i["lon"]
            )
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

    df = pd.DataFrame(candidates)

    if df.empty:
        st.error(T("no_hospital"))
        st.table(pd.DataFrame([{"병원": T("no_hospital_row")}]))
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
        f"**{T('selected_hospital')}:** `{selected_name}` · "
        f"{round(sel['거리(km)'],2)} km / {round(sel['도착예상(분)'],1)} 분"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # STEP4: 연락/핫라인
    st.markdown(
        f"<div style='background:white;padding:20px 22px;border-radius:16px;"
        f"box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #e5e9f2;margin-top:14px;'>"
        f"<div style='font-size:18px;font-weight:700;margin-bottom:8px;'>{T('amb_step4')}</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"📍 **{T('addr')}:** {sel['address']}")
        st.markdown(
            f"""
            <a href="tel:{sel['phone']}">
                <button style="padding:8px 18px;background:#2563EB;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    📞 {sel['phone']}
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
                    🏥 Website
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.write(f"🚨 **{T('hotline_title')}**")
        st.markdown(
            f"""
            <a href="tel:{HOTLINE}">
                <button style="padding:10px 22px;background:#DC2626;color:white;
                               border:none;border-radius:999px;font-size:17px;">
                    🚨 {HOTLINE}
                </button>
            </a>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # STEP5: 지도 + 클릭 출발지 + 네이버 길찾기
    st.markdown(
        f"<div style='background:white;padding:20px 22px;border-radius:16px;"
        f"box-shadow:0 4px 16px rgba(15,23,42,0.08);border:1px solid #e5e9f2;margin-top:14px;'>"
        f"<div style='font-size:18px;font-weight:700;margin-bottom:8px;'>{T('amb_step5')}</div>",
        unsafe_allow_html=True,
    )

    dist, eta, path = get_route_osrm(
        st.session_state.start_lat,
        st.session_state.start_lon,
        sel["lat"],
        sel["lon"],
    )

    st.write(
        T("distance_eta").format(dist=round(dist, 2), eta=round(eta, 1))
    )
    st.write(T("start_from").format(name=current_start_name()))
    st.info(T("map_click_hint"))

    # 지도 중심 좌표 (여기가 빠져 있으면 NameError 발생)
    center_lat = (st.session_state.start_lat + sel["lat"]) / 2
    center_lon = (st.session_state.start_lon + sel["lon"]) / 2

    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # 출발지 마커
    folium.CircleMarker(
        location=[st.session_state.start_lat, st.session_state.start_lon],
        radius=9,
        color="#2563EB",
        fill=True,
        fill_opacity=0.9,
        popup=current_start_name(),
    ).add_to(fmap)

    # 도착지 마커
    folium.CircleMarker(
        location=[sel["lat"], sel["lon"]],
        radius=9,
        color="#EF4444",
        fill=True,
        fill_opacity=0.9,
        popup=selected_name,
    ).add_to(fmap)

    # 경로 polyline (lon,lat → lat,lon)
    route_latlng = [(p[1], p[0]) for p in path]
    folium.PolyLine(
        locations=route_latlng,
        weight=5,
        color="#10B981",
        opacity=0.8,
    ).add_to(fmap)

    # 후보 출발지 마커
    if st.session_state.candidate_lat is not None and st.session_state.candidate_lon is not None:
        folium.CircleMarker(
            location=[st.session_state.candidate_lat, st.session_state.candidate_lon],
            radius=7,
            color="#FBBF24",
            fill=True,
            fill_opacity=0.9,
            popup="Candidate start",
        ).add_to(fmap)

    map_data = st_folium(fmap, height=420, width="100%")

    # 지도 클릭 → 후보 위치 저장
    if map_data and map_data.get("last_clicked"):
        cl = map_data["last_clicked"]
        st.session_state.candidate_lat = cl["lat"]
        st.session_state.candidate_lon = cl["lng"]

    # 후보 위치 정보 + 출발지로 확정 버튼
    if st.session_state.candidate_lat is not None and st.session_state.candidate_lon is not None:
        st.markdown(
            T("map_click_selected").format(
                lat=round(st.session_state.candidate_lat, 5),
                lon=round(st.session_state.candidate_lon, 5),
            )
        )
        if st.button(T("map_click_set_button")):
            st.session_state.start_lat = st.session_state.candidate_lat
            st.session_state.start_lon = st.session_state.candidate_lon
            if st.session_state.lang == "ko":
                st.session_state.start_name_ko = "지도에서 선택한 위치"
                st.session_state.start_name_en = "Selected point on map"
            else:
                st.session_state.start_name_en = "Selected point on map"
                st.session_state.start_name_ko = "지도에서 선택한 위치"
            st.success("출발지가 지도에서 선택한 위치로 변경되었습니다.")
            st.session_state.candidate_lat = None
            st.session_state.candidate_lon = None

    # 네이버 지도 길찾기 링크
    start_lat = st.session_state.start_lat
    start_lon = st.session_state.start_lon
    start_name = current_start_name()
    dest_lat = sel["lat"]
    dest_lon = sel["lon"]

    nmap_url = (
        "nmap://route/car?"
        f"slat={start_lat}&slng={start_lon}&sname={start_name}&"
        f"dlat={dest_lat}&dlng={dest_lon}&dname={selected_name}&"
        "appname=goldentime"
    )

    web_url = (
        "https://map.naver.com/v5/directions/-/-/"
        f"{start_lon},{start_lat}/{dest_lon},{dest_lat}/0?c=14,0,0,0,dh"
    )

    st.markdown(
        f"""
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px;">
            <a href="{nmap_url}">
                <button style="padding:9px 18px;background:#03C75A;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    {T('nav_app_btn')}
                </button>
            </a>
            <a href="{web_url}" target="_blank">
                <button style="padding:9px 18px;background:#111827;color:white;
                               border:none;border-radius:999px;font-size:15px;">
                    {T('nav_web_btn')}
                </button>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

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

HOTLINE = "010-9053-0540"

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


def with_defaults(custom_dict):
    base = empty_treats()
    base.update(custom_dict)
    return base


# ------------------------------------------
# 병원 데이터 (추가 병원 포함, 발작 제거 반영)
# ------------------------------------------
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
# 세션 상태 초기화 + 구조 보정 (KeyError 방지)
# ------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }
else:
    # 새로 추가된 병원 / 병명 자동 보정
    for h, info in HOSPITALS.items():
        if h not in st.session_state.hospital_treats:
            st.session_state.hospital_treats[h] = dict(info["treats_default"])
        else:
            for d in DISEASES:
                st.session_state.hospital_treats[h].setdefault(d, False)


# ==========================================================
#                    HOME 화면 (단순 버전)
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
#                    병원 모드
# ==========================================================
elif st.session_state.page == "hospital":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader("🏥 병원 모드")
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # 병원 선택 + 체크리스트
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

    # 병원 정보 + 위치
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
#                    구급차 모드
# ==========================================================
elif st.session_state.page == "ambulance":
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.subheader("🚑 구급차 모드")
    with top_right:
        if st.button("⬅ 홈으로"):
            st.session_state.page = "home"

    # ---------- 출발 위치 설정 (GPS + 기본 하나고) ----------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">1. 출발 위치 선택</div>', unsafe_allow_html=True)

    start_lat = DEFAULT_LAT
    start_lon = DEFAULT_LON
    start_name = DEFAULT_START_NAME

    st.write(f"기본 출발지: **{DEFAULT_START_NAME} (은평구 연서로 535)**")

    if GEO_AVAILABLE:
        st.info("📡 GPS 버튼을 누르면 현재 기기 위치를 사용합니다. (브라우저에서 위치 권한 허용 필요)")
        if st.button("📍 GPS로 현재 위치 가져오기"):
            loc = streamlit_geolocation()
            if isinstance(loc, dict) and loc.get("latitude") and loc.get("longitude"):
                start_lat = loc["latitude"]
                start_lon = loc["longitude"]
                start_name = "현재 위치"
                st.success(f"현재 위치 사용: 위도 {start_lat:.5f}, 경도 {start_lon:.5f}")
            else:
                st.warning("위치 정보를 가져오지 못했습니다. 기본 위치(하나고)를 계속 사용합니다.")
    else:
        st.info("⚠ GPS 기능을 사용하려면 `streamlit-geolocation` 패키지를 설치해야 합니다.\n\n`pip install streamlit-geolocation` 후 requirements.txt 에도 추가해 주세요.")

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------- 병명 선택 ----------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">2. 병명 선택</div>', unsafe_allow_html=True)
    disease = st.radio("환자의 병명을 선택하세요.", DISEASES, horizontal=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------- 수용 가능 병원 필터링 ----------
    candidates = []
    for h, i in HOSPITALS.items():
        # KeyError 방지를 위해 get 사용
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

    # ---------- 병원 선택 테이블 ----------
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
        update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.MODEL_CHANGED,
        height=260,
        theme="balham",
    )

    raw_sel = grid.get("selected_rows", [])

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

    # ---------- 연락 / 핫라인 ----------
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

    # ---------- 지도 + 네이버 길찾기 ----------
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">5. 지도 및 길안내</div>', unsafe_allow_html=True)

    dist, eta, path = get_route_osrm(
        start_lat, start_lon, sel["lat"], sel["lon"]
    )

    st.write(
        f"🛣 도로 기준 거리: **{round(dist,2)} km**, 예상 소요 시간: **{round(eta,1)} 분**"
    )
    st.write(f"출발지: **{start_name}**")

    ambulance_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": start_lat, "lon": start_lon}],
        get_position="[lon, lat]",
        get_radius=320,
        get_color=[37, 99, 235],
    )

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": sel["lat"], "lon": sel["lon"]}],
        get_position="[lon, lat]",
        get_radius=340,
        get_color=[239, 68, 68],
    )

    path_layer = pdk.Layer(
        "PathLayer",
        data=[{"path": path}],
        get_path="path",
        get_width=6,
        get_color=[16, 185, 129],
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[ambulance_layer, hospital_layer, path_layer],
            initial_view_state=pdk.ViewState(
                latitude=(start_lat + sel["lat"]) / 2,
                longitude=(start_lon + sel["lon"]) / 2,
                zoom=13,
            ),
            tooltip={"text": "응급 이송 경로"},
        )
    )

    # 네이버 지도 길찾기 (앱용 nmap://)
    nmap_url = (
        "nmap://route/car?"
        f"slat={start_lat}&slng={start_lon}&sname={start_name}&"
        f"dlat={sel['lat']}&dlng={sel['lon']}&dname={selected_name}&"
        "appname=goldentime"
    )

    # 웹 브라우저용 네이버 지도 (fallback)
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
