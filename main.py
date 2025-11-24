# app.py

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

DEFAULT_LAT = 37.641240416205285
DEFAULT_LON = 126.93756984090838

HOTLINE = "010-5053-6831"

DISEASES = ["심근경색", "뇌출혈", "뇌진탕", "심장마비", "뇌졸증", "발작"]

HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160,
        "lon": 126.9170,
        "address": "서울특별시 은평구 연서로 177",
        "phone": "02-111-2222",
        "treats_default": {"심근경색": False,"뇌출혈": False,"뇌진탕": True,"심장마비": False,"뇌졸증": True,"발작": True}
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370, "lon": 126.9190,
        "address": "서울특별시 은평구 통일로 1021",
        "phone": "02-222-3333",
        "treats_default": {"심근경색": True,"뇌출혈": True,"뇌진탕": False,"심장마비": True,"뇌졸증": True,"발작": False}
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,"lon": 126.9232331,
        "address": "서울특별시 은평구 백련산로 90",
        "phone": "02-444-5555",
        "treats_default": {"심근경색": False,"뇌출혈": True,"뇌진탕": True,"심장마비": False,"뇌졸증": True,"발작": True}
    },
    "본 서부병원": {
        "lat": 37.6050,"lon": 126.9090,
        "address": "서울특별시 은평구 은평로 133",
        "phone": "02-666-7777",
        "treats_default": {"심근경색": True,"뇌출혈": False,"뇌진탕": True,"심장마비": False,"뇌졸증": False,"발작": True}
    },
    "청구 성심 병원": {
        "lat": 37.6290,"lon": 126.9220,
        "address": "서울특별시 은평구 통일로 873",
        "phone": "02-777-8888",
        "treats_default": {"심근경색": True,"뇌출혈": True,"뇌진탕": False,"심장마비": True,"뇌졸증": True,"발작": True}
    },
}

# ------------------------------------------
# 거리 계산
# ------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ------------------------------------------
# OSRM 도로 기반 경로 계산
# ------------------------------------------
def get_route_osrm(lat1, lon1, lat2, lon2):
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        r = requests.get(url, timeout=5).json()
        route = r["routes"][0]
        distance_km = route["distance"] / 1000
        duration_min = route["duration"] / 60
        coords = route["geometry"]["coordinates"]
        path = [[c[0], c[1]] for c in coords]
        return distance_km, duration_min, path
    except:
        d = haversine(lat1, lon1, lat2, lon2)
        return d, d / 50 * 60, [[lon1, lat1], [lon2, lat2]]

# ------------------------------------------
# 세션 설정
# ------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"]) for h, info in HOSPITALS.items()
    }


# ------------------------------------------
# HOME 화면
# ------------------------------------------
if st.session_state.page == "home":
    st.markdown(
        """
        <div style="display:flex;justify-content:center;align-items:center;height:70vh;">
            <div style="text-align:center;">
                <h1>⏱ 골든 타임</h1>
                <h3>은평 응급 이송 매칭 시스템</h3><br>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(
            """
            <style>
            .big-btn button {
                font-size: 22px !important;
                padding: 18px 24px !important;
                border-radius: 12px !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        if st.button("🏥 병원 모드", use_container_width=True, key="h1"):
            st.session_state.page = "hospital"

        if st.button("🚑 구급차 모드", use_container_width=True, key="h2"):
            st.session_state.page = "ambulance"


# ------------------------------------------
# 병원 모드
# ------------------------------------------
elif st.session_state.page == "hospital":
    st.header("🏥 병원 모드")
    st.button("⬅ 홈으로", on_click=lambda: st.session_state.update(page="home"))

    hospital = st.selectbox("병원을 선택하세요.", list(HOSPITALS.keys()))
    info = HOSPITALS[hospital]

    st.subheader("① 치료 가능 병명 체크리스트")

    for d in DISEASES:
        st.session_state.hospital_treats[hospital][d] = st.checkbox(
            d, value=st.session_state.hospital_treats[hospital][d]
        )

    st.subheader("② 병원 정보")
    st.write(f"📍 주소: {info['address']}")

    st.markdown(
        f"""
        <a href="tel:{info['phone']}">
            <button style="padding:10px 20px;background:#5c7cff;color:white;border:none;border-radius:8px;">
            📞 {info['phone']} 전화걸기
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.subheader("③ 병원 위치")
    st.map(pd.DataFrame([{"lat": info["lat"], "lon": info["lon"]}]))


# ------------------------------------------
# 구급차 모드
# ------------------------------------------
elif st.session_state.page == "ambulance":
    st.header("🚑 구급차 모드")
    st.button("⬅ 홈으로", on_click=lambda: st.session_state.update(page="home"))

    map_placeholder = st.empty()

    st.subheader("① 내 위치 (하나고)")

    base_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": DEFAULT_LAT, "lon": DEFAULT_LON, "name": "내 위치"}],
        get_position="[lon, lat]",
        get_color=[0, 0, 255],
        get_radius=120,
    )
    base_view = pdk.ViewState(latitude=DEFAULT_LAT, longitude=DEFAULT_LON, zoom=13)
    map_placeholder.pydeck_chart(pdk.Deck(layers=[base_layer], initial_view_state=base_view))

    st.subheader("② 병명 선택")
    disease = st.radio("병명을 선택하세요.", DISEASES, horizontal=True)

    # 치료 가능 병원 필터
    candidates = []
    for h, i in HOSPITALS.items():
        if st.session_state.hospital_treats[h][disease]:
            dist, eta, _ = get_route_osrm(DEFAULT_LAT, DEFAULT_LON, i["lat"], i["lon"])
            candidates.append({
                "병원": h,
                "거리(km)": round(dist, 2),
                "도착예상(분)": round(eta, 1),
                "address": i["address"],
                "phone": i["phone"],
                "lat": i["lat"],
                "lon": i["lon"],
            })

    df = pd.DataFrame(candidates).sort_values("도착예상(분)").reset_index(drop=True)

    # 위도, 경도 제거하여 깔끔하게 표시
    display_df = df[["병원", "거리(km)", "도착예상(분)", "address", "phone"]]

    st.subheader("③ 병원 선택 (표를 클릭하세요)")

    gob = GridOptionsBuilder.from_dataframe(display_df)
    gob.configure_selection("single", use_checkbox=True)

    grid = AgGrid(
        display_df,
        gridOptions=gob.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="balham",
        height=260
    )

    selected_rows = grid.get("selected_rows", [])

    if selected_rows:
        selected_hosp = selected_rows[0]["병원"]
    else:
        selected_hosp = display_df.iloc[0]["병원"]

    sel = df[df["병원"] == selected_hosp].iloc[0]

    st.success(f"🚨 선택된 병원: {selected_hosp}")
    st.write(f"📍 주소: {sel['address']}")

    # 병원 전화 연결 버튼
    st.markdown(
        f"""
        <a href="tel:{sel['phone']}">
            <button style="padding:10px 20px;background:#337afe;color:white;border:none;border-radius:8px;">
            📞 {sel['phone']} 전화걸기
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.subheader("④ 응급 핫라인 전화")

    st.markdown(
        f"""
        <a href="tel:{HOTLINE}">
            <button style="padding:14px 28px;background:#ff4444;color:white;border:none;border-radius:12px;font-size:20px;">
            🚨 {HOTLINE} 긴급전화
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    dist, eta, path = get_route_osrm(DEFAULT_LAT, DEFAULT_LON, sel["lat"], sel["lon"])

    st.subheader("⑤ 도로 기준 최단 경로")

    path_layer = pdk.Layer("PathLayer", data=[{"path": path}], get_path="path",
                           get_color=[0, 255, 0], get_width=6)

    amb_layer = pdk.Layer("ScatterplotLayer",
                          data=[{"lat": DEFAULT_LAT, "lon": DEFAULT_LON}],
                          get_position="[lon, lat]", get_color=[0, 0, 255],
                          get_radius=120)

    hosp_layer = pdk.Layer("ScatterplotLayer",
                           data=[{"lat": sel["lat"], "lon": sel["lon"]}],
                           get_position="[lon, lat]", get_color=[255, 0, 0],
                           get_radius=120)

    center_lat = (DEFAULT_LAT + sel["lat"]) / 2
    center_lon = (DEFAULT_LON + sel["lon"]) / 2

    map_placeholder.pydeck_chart(
        pdk.Deck(
            layers=[amb_layer, hosp_layer, path_layer],
            initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=13),
            tooltip={"text": "{name}"}
        )
    )
