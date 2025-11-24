# app.py
# streamlit run app.py 로 실행하세요.

import math
import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="은평 응급 이송 매칭 시스템", layout="wide")

st.title("🚑 은평 응급 이송 매칭 시스템 (예시)")

# -----------------------------
# 데이터 정의
# -----------------------------
DISEASES = ["심근경색", "뇌출혈", "뇌진탕", "심장마비", "뇌졸증", "발작"]

# 병원 좌표 (예시용, 실제와 약간 다를 수 있음)
HOSPITALS = {
    "은평 연세 병원": {
        "lat": 37.6160,
        "lon": 126.9170,
        "treats": ["뇌진탕", "발작", "뇌졸증"],
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370,
        "lon": 126.9190,
        "treats": ["심근경색", "심장마비", "뇌출혈", "뇌졸증"],
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,  # 위키 좌표 기준
        "lon": 126.9232331,
        "treats": ["뇌출혈", "뇌진탕", "뇌졸증", "발작"],
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "treats": ["뇌진탕", "발작", "심근경색"],
    },
    "청구 성심병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "treats": ["심근경색", "심장마비", "뇌출혈", "뇌졸증", "발작"],
    },
}


def haversine(lat1, lon1, lat2, lon2):
    """두 좌표(위도/경도) 사이의 거리(km)를 계산"""
    R = 6371  # 지구 반지름(km)
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return R * c


# -----------------------------
# 공통 UI : 사용자 유형 선택
# -----------------------------
user_type = st.radio("사용자 유형을 선택하세요.", ["🏥 병원", "🚑 구급차"], horizontal=True)

# -----------------------------
# 병원 모드
# -----------------------------
if user_type == "🏥 병원":
    st.subheader("병원 설정 화면")

    hospital_name = st.selectbox("병원을 선택하세요.", list(HOSPITALS.keys()))

    default_treats = HOSPITALS[hospital_name]["treats"]
    selected_treats = st.multiselect(
        "이 병원에서 받을 수 있는 환자 종류를 선택하세요.",
        DISEASES,
        default=default_treats,
    )

    st.info(
        "※ 실제 진료 가능 여부와는 무관한 예시용 프로그램입니다.\n"
        "   선택한 환자 종류는 이 화면에서만 사용됩니다."
    )

    st.markdown("---")
    st.markdown("### 병원 정보 요약")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**병원 이름:** {hospital_name}")
        st.write("**수용 가능한 환자 종류:**")
        if selected_treats:
            st.write(" · " + "\n · ".join(selected_treats))
        else:
            st.write("현재 선택된 환자 종류가 없습니다.")

    with col2:
        # 지도 표시 (해당 병원 위치만)
        lat = HOSPITALS[hospital_name]["lat"]
        lon = HOSPITALS[hospital_name]["lon"]

        hospital_df = pd.DataFrame(
            [{"name": hospital_name, "lat": lat, "lon": lon}]
        )

        view_state = pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=14,
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=hospital_df,
            get_position="[lon, lat]",
            get_radius=80,
            get_color="[255, 0, 0, 200]",
            pickable=True,
        )

        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v11",
            initial_view_state=view_state,
            layers=[layer],
            tooltip={"text": "{name}"},
        )

        st.pydeck_chart(deck)

# -----------------------------
# 구급차 모드
# -----------------------------
else:
    st.subheader("구급차(119) 화면")

    disease = st.selectbox("환자의 병명을 선택하세요.", DISEASES)

    st.markdown("#### 현재 구급차 위치 (위도/경도 입력, 기본값은 은평구 중심부 예시입니다.)")
    col1, col2 = st.columns(2)
    with col1:
        amb_lat = st.number_input(
            "위도(latitude)",
            value=37.618500,
            format="%.6f",
        )
    with col2:
        amb_lon = st.number_input(
            "경도(longitude)",
            value=126.927800,
            format="%.6f",
        )

    # 해당 질환을 치료할 수 있는 병원 필터링
    candidate_hospitals = []
    for name, info in HOSPITALS.items():
        if disease in info["treats"]:
            dist = haversine(amb_lat, amb_lon, info["lat"], info["lon"])
            candidate_hospitals.append(
                {
                    "병원명": name,
                    "lat": info["lat"],
                    "lon": info["lon"],
                    "거리_km": round(dist, 2),
                }
            )

    if not candidate_hospitals:
        st.error("이 병명을 치료할 수 있는 병원이 목록에 없습니다. (예시 데이터 한계)")
    else:
        candidate_df = pd.DataFrame(candidate_hospitals).sort_values("거리_km")
        best = candidate_df.iloc[0]

        st.markdown("### ✅ 추천 병원")
        st.success(
            f"'{disease}' 환자에게 가장 가까운 병원은 **{best['병원명']}** 입니다.\n\n"
            f"직선 거리 기준 약 **{best['거리_km']} km** 떨어져 있습니다."
        )

        st.markdown("### 후보 병원 목록")
        st.dataframe(candidate_df.reset_index(drop=True))

        # 지도에 구급차 위치 + 병원 위치 + 추천 병원까지 선 표시
        hospitals_map_df = candidate_df.copy()
        hospitals_map_df["type"] = "병원"

        ambulance_df = pd.DataFrame(
            [{"name": "구급차 현재 위치", "lat": amb_lat, "lon": amb_lon, "type": "구급차"}]
        )

        # 선(라인) 데이터: 구급차 -> 추천 병원
        line_data = pd.DataFrame(
            [
                {
                    "from_lon": amb_lon,
                    "from_lat": amb_lat,
                    "to_lon": best["lon"],
                    "to_lat": best["lat"],
                }
            ]
        )

        center_lat = (amb_lat + best["lat"]) / 2
        center_lon = (amb_lon + best["lon"]) / 2

        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=13,
        )

        hospital_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hospitals_map_df,
            get_position="[lon, lat]",
            get_radius=80,
            get_color="[255, 0, 0, 200]",  # 병원: 빨간색
            pickable=True,
            get_tooltip="병원명",
        )

        ambulance_layer = pdk.Layer(
            "ScatterplotLayer",
            data=ambulance_df,
            get_position="[lon, lat]",
            get_radius=90,
            get_color="[0, 0, 255, 200]",  # 구급차: 파란색
            pickable=True,
        )

        line_layer = pdk.Layer(
            "LineLayer",
            data=line_data,
            get_source_position="[from_lon, from_lat]",
            get_target_position="[to_lon, to_lat]",
            get_width=5,
            get_color="[0, 255, 0, 200]",  # 경로: 초록색 직선
        )

        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v11",
            initial_view_state=view_state,
            layers=[hospital_layer, ambulance_layer, line_layer],
            tooltip={"text": "{name}"},
        )

        st.markdown("### 지도 (은평구 일대 예시 지도)")
        st.pydeck_chart(deck)
