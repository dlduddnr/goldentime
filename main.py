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

HOTLINE = "010-9053-0540"


# ------------------------------------------
# 병명 리스트 (중복 제거 완료)
# ------------------------------------------
DISEASES = [
    "심근경색",
    "뇌출혈",
    "뇌진탕",
    "심장마비",
    "뇌졸중",  # ← 중복 하나로 통합
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


def with_defaults(custom):
    base = empty_treats()
    base.update(custom)
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
        "treats_default": with_defaults({
            "뇌진탕": True,
            "뇌졸중": True,
            "발작": True
        }),
    },
    "가톨릭대 은평 성모병원": {
        "lat": 37.6370,
        "lon": 126.9190,
        "address": "서울특별시 은평구 통일로 1021",
        "phone": "02-222-3333",
        "website": "https://www.cmcseoul.or.kr",
        "treats_default": with_defaults({
            "심근경색": True,
            "뇌출혈": True,
            "뇌졸중": True,
            "심장마비": True,
        }),
    },
    "서울 특별시 은평병원": {
        "lat": 37.5940039,
        "lon": 126.9232331,
        "address": "서울특별시 은평구 백련산로 90",
        "phone": "02-444-5555",
        "website": "http://epmhc.or.kr",
        "treats_default": with_defaults({
            "뇌출혈": True,
            "뇌진탕": True,
            "뇌졸중": True,
            "발작": True,
        }),
    },
    "본 서부병원": {
        "lat": 37.6050,
        "lon": 126.9090,
        "address": "서울특별시 은평구 은평로 133",
        "phone": "02-666-7777",
        "website": "http://seobuhospital.co.kr",
        "treats_default": with_defaults({
            "심근경색": True,
            "뇌진탕": True,
            "발작": True,
        }),
    },
    "청구 성심 병원": {
        "lat": 37.6290,
        "lon": 126.9220,
        "address": "서울특별시 은평구 통일로 873",
        "phone": "02-777-8888",
        "website": "http://www.chunggu.co.kr",
        "treats_default": with_defaults({
            "심근경색": True,
            "뇌출혈": True,
            "뇌졸중": True,
            "심장마비": True,
            "발작": True,
        }),
    },
}



# ------------------------------------------
# 거리 계산
# ------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))



# ------------------------------------------
# OSRM 경로 계산
# ------------------------------------------
def get_route_osrm(lat1, lon1, lat2, lon2):
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    )
    try:
        r = requests.get(url, timeout=6).json()
        route = r["routes"][0]
        coords = route["geometry"]["coordinates"]
        dist = route["distance"] / 1000
        eta = route["duration"] / 60
        path = [[c[0], c[1]] for c in coords]
        return dist, eta, path
    except:
        d = haversine(lat1, lon1, lat2, lon2)
        return d, d/50*60, [[lon1, lat1], [lon2, lat2]]



# ------------------------------------------
# 세션 초기화
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
                <h1 style="font-size:48px;">⏱ 골든 타임</h1>
                <h3 style="font-size:24px;">은평 응급 이송 매칭 시스템</h3>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    center = st.columns([1,2,1])[1]

    with center:
        if st.button("🏥 병원 모드", use_container_width=True):
            st.session_state.page = "hospital"

        if st.button("🚑 구급차 모드", use_container_width=True):
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
            <button style="padding:12px 24px;background:#4a7cff;color:white;
                           border:none;border-radius:10px;font-size:18px;">
                📞 {info['phone']} 전화걸기
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.subheader("③ 병원 위치")

    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": info["lat"], "lon": info["lon"]}],
        get_position="[lon, lat]",
        get_color=[255, 0, 0],
        get_radius=250,
    )

    view = pdk.ViewState(
        latitude=info["lat"],
        longitude=info["lon"],
        zoom=14
    )

    st.pydeck_chart(pdk.Deck(layers=[hospital_layer], initial_view_state=view))



# ------------------------------------------
# 구급차 모드
# ------------------------------------------
elif st.session_state.page == "ambulance":

    st.header("🚑 구급차 모드")
    st.button("⬅ 홈으로", on_click=lambda: st.session_state.update(page="home"))

    st.write("📍 현재 위치: 하나고등학교")

    st.subheader("① 병명 선택")
    disease = st.radio("병명을 선택하세요.", DISEASES, horizontal=True)

    # 치료 가능 병원 필터링
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
                "website": i["website"],
                "lat": i["lat"],
                "lon": i["lon"],
            })

    st.subheader("② 병원 선택")

    df = pd.DataFrame(candidates)

    # ------------------------------
    # 🚫 치료 가능한 병원이 없는 경우
    # ------------------------------
    if df.empty:
        st.error("🚫 이 병명을 치료할 수 있는 병원이 없습니다.")
        st.table(pd.DataFrame([{"병원": "병원 없음"}]))
        st.stop()

    # 표시용 DF
    display_df = df[["병원", "거리(km)", "도착예상(분)", "address", "phone"]]

    # AgGrid 설정
    gob = GridOptionsBuilder.from_dataframe(display_df)
    gob.configure_selection("single", use_checkbox=True)

    grid = AgGrid(
        display_df,
        gridOptions=gob.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=250,
        theme="balham",
    )

    raw = grid.get("selected_rows", [])

    # ------------------------------------
    #  병원선택 안정화 (❗중요) 
    # ------------------------------------
    if isinstance(raw, list) and len(raw) > 0:
        sel = raw[0]  # 🔥 선택된 병원 dict 그대로 사용
    else:
        sel = display_df.iloc[0].to_dict()  # 기본 1순위

    selected_hospital = sel["병원"]

    st.success(f"🚨 선택된 병원: {selected_hospital}")
    st.write(f"📍 주소: {sel['address']}")

    # 병원 전화 버튼
    st.markdown(
        f"""
        <a href="tel:{sel['phone']}">
            <button style="padding:12px 24px;background:#4e8cff;color:white;
                           border:none;border-radius:10px;font-size:18px;margin-right:5px;">
                📞 {sel['phone']} 전화걸기
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    # 병원 홈페이지 버튼
    st.markdown(
        f"""
        <a href="{sel['website']}" target="_blank">
            <button style="padding:12px 24px;background:#6a4cff;color:white;
                           border:none;border-radius:10px;font-size:18px;">
                🏥 병원 홈페이지 이동
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

    st.subheader("③ 응급 핫라인")

    st.markdown(
        f"""
        <a href="tel:{HOTLINE}">
            <button style="padding:16px 30px;background:#ff4444;color:white;
                           border:none;border-radius:12px;font-size:22px;">
                🚨 {HOTLINE} 긴급전화
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )


    # ------------------------------------------
    # 지도 표시
    # ------------------------------------------
    st.subheader("④ 지도")

    dist, eta, path = get_route_osrm(
        DEFAULT_LAT, DEFAULT_LON, sel["lat"], sel["lon"]
    )

    # 내 위치
    ambulance_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": DEFAULT_LAT, "lon": DEFAULT_LON}],
        get_position="[lon, lat]",
        get_radius=250,
        get_color=[0, 0, 255],
    )

    # 병원 위치 (큰 점)
    hospital_layer = pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat": sel["lat"], "lon": sel["lon"]}],
        get_position="[lon, lat]",
        get_radius=260,
        get_color=[255, 0, 0],
    )

    # 도로 경로
    path_layer = pdk.Layer(
        "PathLayer",
        data=[{"path": path}],
        get_path="path",
        get_width=6,
        get_color=[0, 255, 0],
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[ambulance_layer, hospital_layer, path_layer],
            initial_view_state=pdk.ViewState(
                latitude=(DEFAULT_LAT + sel["lat"]) / 2,
                longitude=(DEFAULT_LON + sel["lon"]) / 2,
                zoom=13
            ),
        )
    )

    # 내비게이션 버튼
    nav_url = f"https://www.google.com/maps/dir/{DEFAULT_LAT},{DEFAULT_LON}/{sel['lat']},{sel['lon']}"
    st.markdown(
        f"""
        <a href="{nav_url}" target="_blank">
            <button style="margin-top:10px;padding:12px 24px;background:#34a853;color:white;
                           border:none;border-radius:10px;font-size:18px;">
                🧭 지도 앱으로 길안내 열기
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )
