import streamlit as st
import pandas as pd
import pydeck as pdk
import math

# -----------------------------------------------------------
# 기본 설정
# -----------------------------------------------------------
st.set_page_config(page_title="은평 응급 시스템", layout="wide")

# 하나고등학교 기본 위치
DEFAULT_LAT = 37.622132   # 하나고등학교 대략적 위도
DEFAULT_LON = 126.919800  # 하나고등학교 대략적 경도

DISEASES = ["심근경색", "뇌출혈", "뇌진탕", "심장마비", "뇌졸증", "발작"]

# 병원 데이터
HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160,
        "lon": 126.9170,
        "treats": {
            "심근경색": "X",
            "뇌출혈": "X",
            "뇌진탕": "O",
            "심장마비": "X",
            "뇌졸증": "O",
            "발작": "O",
        },
        "phone": "02-111-2222",
        "address": "서울 은평구 ○○로 11",
        "doctor_phone": "010-1111-1111"
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370,
        "lon": 126.9190,
        "treats": {
            "심근경색": "O",
            "뇌출혈": "O",
            "뇌진탕": "X",
            "심장마비": "O",
            "뇌졸증": "O",
            "발작": "X",
        },
        "phone": "02-222-3333",
        "address": "서울 은평구 ○○로 22",
        "doctor_phone": "010-2222-2222"
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,
        "lon": 126.9232331,
        "treats": {
            "심근경색": "X",
            "뇌출혈": "O",
            "뇌진탕": "O",
            "심장마비": "X",
            "뇌졸증": "O",
            "발작": "O",
        },
        "phone": "02-444-5555",
        "address": "서울 은평구 ○○로 44",
        "doctor_phone": "010-4444-4444"
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "treats": {
            "심근경색": "O",
            "뇌출혈": "X",
            "뇌진탕": "O",
            "심장마비": "X",
            "뇌졸증": "X",
            "발작": "O",
        },
        "phone": "02-666-7777",
        "address": "서울 은평구 ○○로 66",
        "doctor_phone": "010-6666-6666"
    },
    "청구 성심병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "treats": {
            "심근경색": "O",
            "뇌출혈": "O",
            "뇌진탕": "X",
            "심장마비": "O",
            "뇌졸증": "O",
            "발작": "O",
        },
        "phone": "02-777-8888",
        "address": "서울 은평구 ○○로 77",
        "doctor_phone": "010-7777-7777"
    },
}

# -----------------------------------------------------------
# 거리 계산
# -----------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lat2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))

# -----------------------------------------------------------
# 네비게이션 API (모의)
# -----------------------------------------------------------
def get_fastest_route(amb_lat, amb_lon, dest_lat, dest_lon):
    """외부 API와 연동될 자리 (카카오 / 네이버 / OSRM 등)
       현재는 직선거리 * 계수로 '예상 도착 시간'만 계산"""
    distance = haversine(amb_lat, amb_lon, dest_lat, dest_lon)
    return distance, distance * 2.1   # (km, minutes)

# -----------------------------------------------------------
# 페이지 전환
# -----------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"


# -----------------------------------------------------------
# HOME PAGE
# -----------------------------------------------------------
if st.session_state.page == "home":
    st.title("🚑 은평 응급 이송 매칭 시스템")

    st.markdown("### 모드를 선택하세요.")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🏥 병원 모드", use_container_width=True):
            st.session_state.page = "hospital"

    with col2:
        if st.button("🚑 구급차 모드", use_container_width=True):
            st.session_state.page = "ambulance"


# -----------------------------------------------------------
# HOSPITAL PAGE
# -----------------------------------------------------------
elif st.session_state.page == "hospital":
    st.header("🏥 병원 모드")

    if st.button("⬅ 돌아가기"):
        st.session_state.page = "home"

    hospital = st.selectbox("병원을 선택하세요.", list(HOSPITALS.keys()))

    info = HOSPITALS[hospital]

    st.subheader("세부 진료과 수술/처치 가능 여부")
    df = pd.DataFrame.from_dict(info["treats"], orient="index", columns=["가능 여부"])
    st.table(df)

    st.subheader("병원 정보")
    st.write(f"**주소:** {info['address']}")
    st.write(f"**대표 번호:** {info['phone']}")
    st.write(f"**의사 핫라인:** {info['doctor_phone']}")

    st.button("📞 응급실 상황실 바로 연결", type="primary")

    # 지도 표시
    hospital_df = pd.DataFrame([{
        "name": hospital,
        "lat": info["lat"],
        "lon": info["lon"],
    }])

    view = pdk.ViewState(latitude=info["lat"], longitude=info["lon"], zoom=14)

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=hospital_df,
        get_position="[lon, lat]",
        get_radius=80,
        get_color=[255, 0, 0, 200],
    )

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view))


# -----------------------------------------------------------
# AMBULANCE PAGE
# -----------------------------------------------------------
elif st.session_state.page == "ambulance":
    st.header("🚑 구급차 모드")

    if st.button("⬅ 돌아가기"):
        st.session_state.page = "home"

    st.subheader("현재 위치 : 하나고등학교 (기본값)")
    amb_lat = DEFAULT_LAT
    amb_lon = DEFAULT_LON

    st.map(pd.DataFrame([{"lat": amb_lat, "lon": amb_lon}]))

    st.subheader("환자의 병명 선택")
    disease = st.radio("증상 선택", DISEASES, horizontal=True)

    # 수용 가능한 병원 필터
    candidates = []
    for name, info in HOSPITALS.items():
        if info["treats"][disease] == "O":
            dist, eta = get_fastest_route(
                amb_lat, amb_lon, info["lat"], info["lon"]
            )
            candidates.append({
                "병원": name,
                "거리(km)": round(dist, 2),
                "도착예상(분)": round(eta, 1),
                "lat": info["lat"],
                "lon": info["lon"],
            })

    df = pd.DataFrame(candidates).sort_values("도착예상(분)")
    st.subheader("📌 최적 병원 추천 (교통 반영)")
    st.write(df)

    best = df.iloc[0]
    st.success(f"🚨 최적 병원: **{best['병원']}** (예상 {best['도착예상(분)']}분)")

    # -----------------------------------------------------------
    # 역경매 방식 병원 수용 요청
    # -----------------------------------------------------------
    st.subheader("📣 응급 환자 수용 요청 (반경 3km)")
    if st.button("📡 반경 내 모든 병원에 요청 보내기"):
        st.info("요청 전송됨. 가장 먼저 수용 가능 버튼을 누른 병원으로 자동 배정됩니다.")
        st.warning("※ 실제 병원 시스템 연동은 API 작업 필요")

    # -----------------------------------------------------------
    # 환자 데이터 전송
    # -----------------------------------------------------------
    st.subheader("📤 환자 데이터 전송")
    ecg = st.file_uploader("심전도 파일 업로드")
    bp = st.text_input("혈압")
    hr = st.text_input("심박수")

    if st.button("🚑 병원으로 전송하기", type="primary"):
        st.success("환자 정보가 병원으로 전송되었습니다! (모의 기능)")

    # 지도 표시
    map_df = pd.DataFrame(df)
    view = pdk.ViewState(latitude=DEFAULT_LAT, longitude=DEFAULT_LON, zoom=13)

    ambulance_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": amb_lat, "lon": amb_lon}]),
        get_position="[lon, lat]",
        get_radius=120,
        get_color=[0, 0, 255, 200],
    )

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_radius=100,
        get_color=[255, 0, 0, 200],
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[ambulance_layer, hospital_layer],
            initial_view_state=view,
            map_style="mapbox://styles/mapbox/streets-v11",
        )
    )
