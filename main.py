# app.py
# streamlit run app.py 로 실행

import streamlit as st
import pandas as pd
import pydeck as pdk
import math

st.set_page_config(page_title="은평 응급 이송 시스템", layout="wide")

# -------------------------
# 기본 위치: 하나고등학교
# -------------------------
DEFAULT_LAT = 37.622132   # 하나고 근처 예시 위도
DEFAULT_LON = 126.919800  # 하나고 근처 예시 경도

DISEASES = ["심근경색", "뇌출혈", "뇌진탕", "심장마비", "뇌졸증", "발작"]

# -------------------------
# 병원 데이터 (주소 수정 반영)
# treats 는 기본값만 설정, 실제 사용 여부는 병원 페이지에서 체크박스로 선택
# -------------------------
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
        "doctor_phone": "010-1111-1111",
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
        "doctor_phone": "010-2222-2222",
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
        "doctor_phone": "010-4444-4444",
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
        "doctor_phone": "010-6666-6666",
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
        "doctor_phone": "010-7777-7777",
    },
}

# --------------------------------
# 거리 / 시간 계산 (현실적인 값으로 조정)
# --------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lat2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

def get_fastest_route(amb_lat, amb_lon, dest_lat, dest_lon):
    """
    실제로는 교통량/경로 API와 연동되는 자리.
    여기서는 직선거리 + 평균 60km/h 속도로 도착 시간 계산.
    """
    distance_km = haversine(amb_lat, amb_lon, dest_lat, dest_lon)
    # 60km/h 가정 → 시간(h) = 거리/60 → 분 = 거리/60*60 = 거리
    # 그래서 '거리(km) ≒ 분' 이 되도록, 약간 느리게 50km/h 정도로 보정
    eta_min = distance_km / 50 * 60   # 50km/h
    return distance_km, eta_min

# --------------------------------
# 세션 상태: 페이지 & 병원별 치료 가능 여부
# --------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {}
    for name, info in HOSPITALS.items():
        st.session_state.hospital_treats[name] = {
            d: info["treats_default"].get(d, False) for d in DISEASES
        }

# --------------------------------
# HOME PAGE
# --------------------------------
if st.session_state.page == "home":
    st.title("🚑 은평 응급 이송 매칭 시스템")

    st.markdown("#### 모드를 선택하세요.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏥 병원 모드", use_container_width=True):
            st.session_state.page = "hospital"
    with c2:
        if st.button("🚑 구급차 모드", use_container_width=True):
            st.session_state.page = "ambulance")

# --------------------------------
# HOSPITAL PAGE
# --------------------------------
elif st.session_state.page == "hospital":
    st.header("🏥 병원 모드")
    if st.button("⬅ 홈으로", key="back_home_from_hospital"):
        st.session_state.page = "home"

    hospital = st.selectbox("병원을 선택하세요.", list(HOSPITALS.keys()))
    info = HOSPITALS[hospital]

    st.subheader("① 이 병원에서 치료할 수 있는 병명 선택")
    st.write("체크리스트에서 이 병원이 수용 가능한 질환을 선택하세요.")

    # 체크리스트 (각 병명별 체크박스)
    for d in DISEASES:
        current = st.session_state.hospital_treats[hospital].get(d, False)
        checked = st.checkbox(
            d,
            value=current,
            key=f"{hospital}_{d}",
        )
        st.session_state.hospital_treats[hospital][d] = checked

    # O/X 테이블 표시
    st.subheader("② 세부 진료과 수술/처치 가능 여부 (O/X)")
    table_data = {
        d: "O" if st.session_state.hospital_treats[hospital][d] else "X"
        for d in DISEASES
    }
    st.table(pd.DataFrame.from_dict(table_data, orient="index", columns=["가능 여부"]))

    st.subheader("③ 병원 기본 정보")
    st.write(f"**주소:** {info['address']}")
    st.write(f"**대표 번호:** {info['phone']}")
    st.write(f"**병원 내 의사 전화번호(예시):** {info['doctor_phone']}")

    st.subheader("④ 핫라인 원터치 연결")
    st.write("원터치 핫라인 번호: **010-9053-0540**")
    # 브라우저/모바일에서 tel: 링크로 실제 전화 앱이 실행됨
    st.markdown(
        """
        <a href="tel:01090530540">
            <button style="padding:10px 20px;font-size:16px;border-radius:8px;
                           border:none;background-color:#ff4b4b;color:white;">
                📞 010-9053-0540 전화걸기
            </button>
        </a>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("⑤ 병원 위치")
    hospital_df = pd.DataFrame(
        [{"name": hospital, "lat": info["lat"], "lon": info["lon"]}]
    )
    view = pdk.ViewState(latitude=info["lat"], longitude=info["lon"], zoom=14)
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=hospital_df,
        get_position="[lon, lat]",
        get_radius=80,
        get_color=[255, 0, 0, 200],
        pickable=True,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view))

# --------------------------------
# AMBULANCE PAGE
# --------------------------------
elif st.session_state.page == "ambulance":
    st.header("🚑 구급차 모드")
    if st.button("⬅ 홈으로", key="back_home_from_ambulance"):
        st.session_state.page = "home"

    st.subheader("① 현재 위치 (기본: 하나고등학교)")
    st.write("주소: 서울특별시 은평구 연서로 535 (하나고등학교)")
    st.map(pd.DataFrame([{"lat": DEFAULT_LAT, "lon": DEFAULT_LON}]))

    amb_lat, amb_lon = DEFAULT_LAT, DEFAULT_LON

    st.subheader("② 환자의 병명 선택")
    disease = st.radio("병명을 선택하세요.", DISEASES, horizontal=True)

    # 병명에 따라 실제로 수용 가능한 병원 필터
    candidates = []
    for name, info in HOSPITALS.items():
        can_treat = st.session_state.hospital_treats[name].get(disease, False)
        if can_treat:
            dist, eta = get_fastest_route(
                amb_lat, amb_lon, info["lat"], info["lon"]
            )
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
        st.error("현재 이 병명을 수용 가능으로 설정한 병원이 없습니다. (병원 모드에서 체크리스트를 확인하세요.)")
        st.stop()

    df = pd.DataFrame(candidates).sort_values("도착예상(분)").reset_index(drop=True)

    st.subheader("③ 수용 가능 병원 목록 (거리 및 도착 시간)")
    st.dataframe(df[["병원", "거리(km)", "도착예상(분)", "address", "phone"]])

    # 기본 추천 병원은 가장 빠른 곳
    best_name = df.iloc[0]["병원"]
    st.success(f"추천 병원: **{best_name}** (예상 {df.iloc[0]['도착예상(분)']}분, 약 {df.iloc[0]['거리(km)']}km)")

    st.subheader("④ 실제 이송할 병원 선택")
    selected_name = st.selectbox("이송 병원을 선택하세요.", df["병원"].tolist(), index=0)
    selected = df[df["병원"] == selected_name].iloc[0]

    st.write(f"선택한 병원: **{selected_name}**")
    st.write(f"주소: {selected['address']} / 대표번호: {selected['phone']}")

    # 하나고 → 선택 병원 최단 경로(직선) 지도
    st.subheader("⑤ 하나고 → 선택 병원 최단(직선) 경로 지도")

    map_df = pd.DataFrame(
        [
            {"name": "구급차(하나고)", "lat": amb_lat, "lon": amb_lon, "type": "ambulance"},
            {"name": selected_name, "lat": selected["lat"], "lon": selected["lon"], "type": "hospital"},
        ]
    )

    line_df = pd.DataFrame(
        [
            {
                "from_lon": amb_lon,
                "from_lat": amb_lat,
                "to_lon": selected["lon"],
                "to_lat": selected["lat"],
            }
        ]
    )

    view = pdk.ViewState(
        latitude=(amb_lat + selected["lat"]) / 2,
        longitude=(amb_lon + selected["lon"]) / 2,
        zoom=13,
    )

    amb_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df[map_df["type"] == "ambulance"],
        get_position="[lon, lat]",
        get_radius=120,
        get_color=[0, 0, 255, 200],
        pickable=True,
    )
    hosp_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df[map_df["type"] == "hospital"],
        get_position="[lon, lat]",
        get_radius=100,
        get_color=[255, 0, 0, 200],
        pickable=True,
    )
    line_layer = pdk.Layer(
        "LineLayer",
        data=line_df,
        get_source_position="[from_lon, from_lat]",
        get_target_position="[to_lon, to_lat]",
        get_width=5,
        get_color=[0, 255, 0, 200],
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[amb_layer, hosp_layer, line_layer],
            initial_view_state=view,
            map_style="mapbox://styles/mapbox/streets-v11",
            tooltip={"text": "{name}"},
        )
    )

    st.info("※ 실제 내비게이션 연동을 하려면 카카오/네이버 지도 등의 경로 API를 연결하면 됩니다.")
