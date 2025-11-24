# app.py
# 실행: streamlit run app.py

import math
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# -------------------------
# 기본 설정
# -------------------------
st.set_page_config(page_title="골든 타임", layout="wide")

# 하나고등학교 (대략 좌표) - 위치 조금 어긋나면 카카오맵/네이버맵에서 위도/경도 복사해서 수정하면 됨
DEFAULT_LAT = 37.6235
DEFAULT_LON = 126.9250

HOTLINE = "010-9053-0540"

DISEASES = ["심근경색", "뇌출혈", "뇌진탕", "심장마비", "뇌졸증", "발작"]

# 병원 데이터
HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160,
        "lon": 126.9170,
        "treats_default": {
            "심근경색": False,
            "뇌출혈": False,
            "뇌진탕": True,
            "심장마비": False,
            "뇌졸증": True,
            "발작": True,
        },
        "phone": "02-111-2222",
        "address": "서울특별시 은평구 연서로 177",
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370,
        "lon": 126.9190,
        "treats_default": {
            "심근경색": True,
            "뇌출혈": True,
            "뇌진탕": False,
            "심장마비": True,
            "뇌졸증": True,
            "발작": False,
        },
        "phone": "02-222-3333",
        "address": "서울특별시 은평구 통일로 1021",
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,
        "lon": 126.9232331,
        "treats_default": {
            "심근경색": False,
            "뇌출혈": True,
            "뇌진탕": True,
            "심장마비": False,
            "뇌졸증": True,
            "발작": True,
        },
        "phone": "02-444-5555",
        "address": "서울특별시 은평구 백련산로 90",
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "treats_default": {
            "심근경색": True,
            "뇌출혈": False,
            "뇌진탕": True,
            "심장마비": False,
            "뇌졸증": False,
            "발작": True,
        },
        "phone": "02-666-7777",
        "address": "서울특별시 은평구 은평로 133",
    },
    "청구 성심 병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "treats_default": {
            "심근경색": True,
            "뇌출혈": True,
            "뇌진탕": False,
            "심장마비": True,
            "뇌졸증": True,
            "발작": True,
        },
        "phone": "02-777-8888",
        "address": "서울특별시 은평구 통일로 873",
    },
}

# -------------------------
# 거리 / 경로 관련 함수
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def get_route_osrm(lat1, lon1, lat2, lon2):
    """
    OSRM 공개 라우팅 서버를 이용해서
    - 도로 기준 거리(km)
    - 예상 소요 시간(분)
    - 경로 좌표 리스트를 반환
    실패하면 직선거리로 fallback
    """
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )
    try:
        res = requests.get(url, timeout=5)
        data = res.json()
        route = data["routes"][0]
        distance_km = route["distance"] / 1000  # m → km
        duration_min = route["duration"] / 60   # s → min
        coords = route["geometry"]["coordinates"]  # [ [lon,lat], ... ]
        path = [[c[0], c[1]] for c in coords]
        return distance_km, duration_min, path
    except Exception:
        # 실패 시 직선거리 기준
        dist = haversine(lat1, lon1, lat2, lon2)
        eta = dist / 50 * 60  # 50km/h
        path = [[lon1, lat1], [lon2, lat2]]
        return dist, eta, path

# -------------------------
# 세션 초기화
# -------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        name: dict(info["treats_default"]) for name, info in HOSPITALS.items()
    }

# -------------------------
# HOME 화면
# -------------------------
if st.session_state.page == "home":
    st.markdown(
        """
        <div style="display:flex;justify-content:center;align-items:center;height:70vh;">
          <div style="text-align:center;">
            <h1>⏱️ 골든 타임</h1>
            <h3>은평 응급 이송 매칭 시스템</h3>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_left:
        pass
    with col_center:
        if st.button("🏥 병원 모드", use_container_width=True):
            st.session_state.page = "hospital"
        if st.button("🚑 구급차 모드", use_container_width=True):
            st.session_state.page = "ambulance"
    with col_right:
        pass

# -------------------------
# 병원 모드
# -------------------------
elif st.session_state.page == "hospital":
    st.header("🏥 병원 모드")
    st.button("⬅ 홈으로", on_click=lambda: st.session_state.update(page="home"))

    hospital = st.selectbox("병원을 선택하세요.", list(HOSPITALS.keys()))
    info = HOSPITALS[hospital]

    st.subheader("① 치료 가능한 병명 체크리스트")
    for d in DISEASES:
        st.session_state.hospital_treats[hospital][d] = st.checkbox(
            d,
            value=st.session_state.hospital_treats[hospital][d],
            key=f"{hospital}_{d}",
        )

    st.subheader("② 치료 가능 여부 (O / X)")
    ox_data = {
        d: "O" if st.session_state.hospital_treats[hospital][d] else "X"
        for d in DISEASES
    }
    st.table(pd.DataFrame.from_dict(ox_data, orient="index", columns=["가능 여부"]))

    st.subheader("③ 병원 정보")
    st.write(f"📍 주소: {info['address']}")
    st.write(f"📞 대표 번호: {info['phone']}")

    st.subheader("④ 병원 위치 지도")
    st.map(pd.DataFrame([{"lat": info["lat"], "lon": info["lon"]}]))

# -------------------------
# 구급차 모드
# -------------------------
elif st.session_state.page == "ambulance":
    st.header("🚑 구급차 모드")
    st.button("⬅ 홈으로", on_click=lambda: st.session_state.update(page="home"))

    # ⭐ 맨 위 지도용 placeholder (선택된 병원에 따라 갱신)
    map_placeholder = st.empty()

    st.subheader("① 내 현재 위치 (하나고등학교 기준)")
    st.write("주소: 서울특별시 은평구 연서로 535 (하나고등학교)")

    # 이 시점에서는 선택한 병원이 아직 없으니까,
    # 기본 지도: 내 위치만 표시
    base_view = pdk.ViewState(
        latitude=DEFAULT_LAT,
        longitude=DEFAULT_LON,
        zoom=13,
    )
    base_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": DEFAULT_LAT, "lon": DEFAULT_LON, "name": "내 위치(하나고)"}],
        get_position="[lon, lat]",
        get_radius=120,
        get_color=[0, 0, 255],
        pickable=True,
    )
    map_placeholder.pydeck_chart(
        pdk.Deck(layers=[base_layer], initial_view_state=base_view, tooltip={"text": "{name}"})
    )

    amb_lat, amb_lon = DEFAULT_LAT, DEFAULT_LON

    st.subheader("② 환자 병명 선택")
    disease = st.radio("병명을 선택하세요.", DISEASES, horizontal=True)

    # 이 병명을 치료할 수 있는 병원 필터
    candidates = []
    for name, info in HOSPITALS.items():
        if st.session_state.hospital_treats[name][disease]:
            dist, eta, _ = get_route_osrm(amb_lat, amb_lon, info["lat"], info["lon"])
            candidates.append(
                {
                    "병원": name,
                    "거리(km)": round(dist, 2),
                    "도착예상(분)": round(eta, 1),
                    "lat": info["lat"],
                    "lon": info["lon"],
                    "address": info["address"],
                    "phone": info["phone"],
                }
            )

    if not candidates:
        st.error("현재 이 병명을 치료 가능으로 설정한 병원이 없습니다. (병원 모드에서 체크리스트 확인 필요)")
        st.stop()

    df = pd.DataFrame(candidates).sort_values("도착예상(분)").reset_index(drop=True)

    st.subheader("③ 수용 가능 병원 목록 (표를 클릭해서 선택)")

    display_df = df[["병원", "거리(km)", "도착예상(분)", "address", "phone"]]

    gob = GridOptionsBuilder.from_dataframe(display_df)
    gob.configure_selection("single", use_checkbox=True)
    gob.configure_grid_options(domLayout="normal")
    grid_options = gob.build()

    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=250,
        theme="balham",
    )

    if grid_response.selected_rows:
        selected_name = grid_response.selected_rows[0]["병원"]
    else:
        selected_name = df.iloc[0]["병원"]  # 아무것도 선택 안 하면 1순위 병원 자동 선택

    selected_row = df[df["병원"] == selected_name].iloc[0]

    st.success(f"🚨 선택된 병원: {selected_name}")
    st.write(f"주소: {selected_row['address']}")
    st.write(f"대표 전화: {selected_row['phone']}")

    # 📞 핫라인 전화 버튼 (구급차 모드에 위치)
    st.subheader("④ 응급 핫라인 전화")
    st.markdown(
        f"""
        <a href="tel:{HOTLINE}">
            <button style="
                padding:12px 24px;
                background:#ff4d4d;
                color:white;
                border:none;
                border-radius:8px;
                font-size:18px;">
                📞 {HOTLINE} 전화 걸기
            </button>
        </a>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------
    # 도로 기준 최단 경로 계산 & 맨 위 지도에 다시 그리기
    # -------------------------
    dist_km, eta_min, path = get_route_osrm(
        amb_lat, amb_lon, selected_row["lat"], selected_row["lon"]
    )

    st.subheader("⑤ 도로 기준 최단 경로 정보")
    st.write(f"• 거리: 약 {dist_km:.2f} km")
    st.write(f"• 예상 소요 시간: 약 {eta_min:.1f} 분")

    # pydeck용 데이터 구성
    path_layer_data = [{"path": path, "name": f"{selected_name} 경로"}]

    ambulance_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": amb_lat, "lon": amb_lon, "name": "내 위치(하나고)"}],
        get_position="[lon, lat]",
        get_radius=120,
        get_color=[0, 0, 255],
        pickable=True,
    )

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{
            "lat": selected_row["lat"],
            "lon": selected_row["lon"],
            "name": selected_name,
        }],
        get_position="[lon, lat]",
        get_radius=120,
        get_color=[255, 0, 0],
        pickable=True,
    )

    route_layer = pdk.Layer(
        "PathLayer",
        data=path_layer_data,
        get_path="path",
        get_width=6,
        get_color=[0, 255, 0],
        pickable=False,
    )

    center_lat = (amb_lat + selected_row["lat"]) / 2
    center_lon = (amb_lon + selected_row["lon"]) / 2

    route_view = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=13,
    )

    # ⭐ 맨 위 map_placeholder에 다시 그리기
    map_placeholder.pydeck_chart(
        pdk.Deck(
            layers=[ambulance_layer, hospital_layer, route_layer],
            initial_view_state=route_view,
            tooltip={"text": "{name}"},
        )
    )
