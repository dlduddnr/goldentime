# app.py
# streamlit run app.py

import streamlit as st
import pandas as pd
import pydeck as pdk
import math

# -------------------------
# 기본 설정
# -------------------------
st.set_page_config(page_title="은평 응급 이송 시스템", layout="wide")

DEFAULT_LAT = 37.622132   # 하나고 위도
DEFAULT_LON = 126.919800  # 하나고 경도

HOTLINE = "010-5053-6831"  # 변경된 전화번호

DISEASES = ["심근경색", "뇌출혈", "뇌진탕", "심장마비", "뇌졸증", "발작"]

# -------------------------
# 병원 데이터
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
# 거리 계산 함수
# -------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def get_fastest_route(a_lat, a_lon, b_lat, b_lon):
    dist = haversine(a_lat, a_lon, b_lat, b_lon)
    eta = dist / 50 * 60  # 50km/h 기준
    return dist, eta

# -------------------------
# 세션 초기화
# -------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"

if "hospital_treats" not in st.session_state:
    st.session_state.hospital_treats = {
        h: dict(info["treats_default"])
        for h, info in HOSPITALS.items()
    }

# -------------------------
# HOME 화면
# -------------------------
if st.session_state.page == "home":

    st.markdown(
        """
        <div style="display:flex;justify-content:center;align-items:center;height:70vh;">
            <div style="text-align:center;">
                <h1>🚑 은평 응급 이송 매칭 시스템</h1><br>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        pass
    with col2:
        if st.button("🏥 병원 모드", use_container_width=True):
            st.session_state.page = "hospital"
        if st.button("🚑 구급차 모드", use_container_width=True):
            st.session_state.page = "ambulance"
    with col3:
        pass


# -------------------------
# 병원 모드
# -------------------------
elif st.session_state.page == "hospital":

    st.header("🏥 병원 모드")
    st.button("⬅ 홈으로", on_click=lambda: st.session_state.update(page="home"))

    hospital = st.selectbox("병원을 선택하세요", list(HOSPITALS.keys()))

    st.subheader("① 치료 가능한 병명 선택 (체크리스트)")

    for d in DISEASES:
        st.session_state.hospital_treats[hospital][d] = st.checkbox(
            d,
            value=st.session_state.hospital_treats[hospital][d],
            key=f"{hospital}_{d}",
        )

    st.subheader("② 병원 정보")
    info = HOSPITALS[hospital]
    st.write(f"📍 주소: {info['address']}")
    st.write(f"📞 대표 번호: {info['phone']}")

    st.subheader("③ 병원 위치 지도")
    st.map(pd.DataFrame([{"lat": info["lat"], "lon": info["lon"]}]))


# -------------------------
# 구급차 모드
# -------------------------
elif st.session_state.page == "ambulance":

    st.header("🚑 구급차 모드")
    st.button("⬅ 홈으로", on_click=lambda: st.session_state.update(page="home"))

    st.subheader("① 현재 위치 (하나고등학교)")
    st.map(pd.DataFrame([{"lat": DEFAULT_LAT, "lon": DEFAULT_LON}]))

    st.subheader("② 병명 선택")
    disease = st.radio("병명을 선택하세요.", DISEASES, horizontal=True)

    # 치료 가능한 병원 필터
    candidates = []
    for h, i in HOSPITALS.items():
        if st.session_state.hospital_treats[h][disease]:
            dist, eta = get_fastest_route(DEFAULT_LAT, DEFAULT_LON, i["lat"], i["lon"])
            candidates.append({
                "병원": h,
                "거리(km)": round(dist, 2),
                "도착예상(분)": round(eta, 1),
                "lat": i["lat"],
                "lon": i["lon"],
                "address": i["address"],
                "phone": i["phone"],
            })

    if not candidates:
        st.error("현재 이 병명을 치료 가능한 병원이 없습니다.")
        st.stop()

    df = pd.DataFrame(candidates).sort_values("도착예상(분)").reset_index(drop=True)

    st.subheader("③ 병원 선택")
    st.dataframe(df)

    selected = st.selectbox("이송할 병원을 선택하세요.", df["병원"])
    sel = df[df["병원"] == selected].iloc[0]

    st.success(f"🚨 선택된 병원: {selected}")
    st.write(f"주소: {sel['address']}")
    st.write(f"전화번호: {sel['phone']}")

    # -------------------------
    # ★ 전화 버튼을 구급차 모드로 이동!
    # -------------------------
    st.subheader("📞 응급 핫라인")
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
    # 지도: 하나고 → 선택 병원
    # -------------------------
    st.subheader("④ 최단 경로 지도")

    line_df = pd.DataFrame([{
        "from_lon": DEFAULT_LON,
        "from_lat": DEFAULT_LAT,
        "to_lon": sel["lon"],
        "to_lat": sel["lat"],
    }])

    view = pdk.ViewState(
        latitude=(DEFAULT_LAT + sel["lat"]) / 2,
        longitude=(DEFAULT_LON + sel["lon"]) / 2,
        zoom=13,
    )

    layer_amb = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": DEFAULT_LAT, "lon": DEFAULT_LON}]),
        get_position="[lon, lat]",
        get_radius=100,
        get_color=[0, 0, 255],
    )

    layer_hosp = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": sel["lat"], "lon": sel["lon"]}]),
        get_position="[lon, lat]",
        get_radius=100,
        get_color=[255, 0, 0],
    )

    line_layer = pdk.Layer(
        "LineLayer",
        data=line_df,
        get_source_position="[from_lon, from_lat]",
        get_target_position="[to_lon, to_lat]",
        get_width=5,
        get_color=[0, 255, 0],
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer_amb, layer_hosp, line_layer],
            initial_view_state=view
        )
    )
