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
        "home_hint": "사용할 모드를 선택해주세요.",
        "back_home": "⬅ 홈으로",
        "hospital_title": "🏥 병원 모드",
        "hospital_step1": "1. 병원 선택 & 수용 가능 병명 체크",
        "hospital_step2": "2. 병원 정보 확인",
        "hospital_select": "병원 선택",
        "hospital_check_desc": "이 병원이 치료 가능한 항목을 체크해 주세요:",
        "hospital_map": "위치 확인",
        "ambulance_title": "🚑 구급차 모드",
        "amb_step1": "1. 출발 위치 선택",
        "amb_step2": "2. 병명 선택",
        "amb_step3": "3. 수용 가능 병원 선택",
        "amb_step4": "4. 연락 및 핫라인",
        "amb_step5": "5. 지도 및 길안내",
        "disease_prompt": "환자 상태(병명)를 선택하세요:",
        "no_hospital": "🚫 이 병명을 수용 가능한 병원이 없습니다.",
        "selected_hospital": "선택된 병원",
        "addr": "주소",
        "gps_not_available": "⚠ GPS 기능을 사용하려면 streamlit-geolocation이 필요합니다.",
        "distance_eta": "거리: {dist} km / 예상 {eta} 분",
        "map_click_hint": "🖱 지도 위를 클릭하면 새로운 출발지 후보가 표시됩니다.",
        "map_click_set_button": "이 위치로 출발지 설정",
        "nav_app_btn": "🧭 네이버 지도 앱으로 길 안내",
        "nav_web_btn": "🌐 네이버 지도 웹 열기",
    },
    "en": {
        "app_title": "⏱ Golden Time",
        "app_subtitle": "Emergency Transport System",
        "lang_label": "Language / 언어 선택",
        "mode_hospital": "🏥 Hospital Mode",
        "mode_ambulance": "🚑 Ambulance Mode",
        "home_hint": "Please select a mode.",
        "back_home": "⬅ Back to Home",
        "hospital_title": "🏥 Hospital Mode",
        "hospital_step1": "1. Select hospital & treatable diseases",
        "hospital_step2": "2. Hospital information",
        "hospital_select": "Select hospital",
        "hospital_check_desc": "Check possible treatments:",
        "hospital_map": "Map View",
        "ambulance_title": "🚑 Ambulance Mode",
        "amb_step1": "1. Choose starting point",
        "amb_step2": "2. Select disease",
        "amb_step3": "3. Select available hospital",
        "amb_step4": "4. Contact & Hotline",
        "amb_step5": "5. Map & Navigation",
        "disease_prompt": "Select disease:",
        "no_hospital": "🚫 No hospital available.",
        "selected_hospital": "Selected hospital",
        "addr": "Address",
        "gps_not_available": "⚠ GPS requires streamlit-geolocation.",
        "distance_eta": "Distance: {dist} km / ETA {eta} min",
        "map_click_hint": "🖱 Click on map to select new start point.",
        "map_click_set_button": "Set start here",
        "nav_app_btn": "🧭 Navigate in Naver Map app",
        "nav_web_btn": "🌐 Open Naver Map (Web)",
    }
}

def T(key):  
    return TEXT[st.session_state.get("lang","ko")][key]

# ------------------------------------------
# 병명
# ------------------------------------------
DISEASES = [
    "심근경색","뇌출혈","뇌진탕","심장마비","뇌졸중",
    "급성 복막염","기흉","폐색전증","패혈증","급성 심부전",
    "뇌수막염","대량 위장관 출혈","아나필락시스"
]

def empty_treats():
    return {d: False for d in DISEASES}

def with_defaults(d):  
    base = empty_treats()
    base.update(d)
    return base

# ------------------------------------------
# 병원 데이터
# ------------------------------------------
HOSPITALS = {
    "은평 연세 병원": {
        "lat":37.6160, "lon":126.9170,
        "address":"서울특별시 은평구 연서로 177",
        "treats_default":with_defaults({"뇌졸중":True})
    },
    "가톨릭대 은평 성모병원": {
        "lat":37.6370, "lon":126.9190,
        "address":"서울특별시 은평구 통일로 1021",
        "treats_default":with_defaults({"심근경색":True,"뇌출혈":True})
    },
    "서울특별시 은평병원": {
        "lat":37.5940, "lon":126.9232,
        "address":"서울특별시 은평구 백련산로 90",
        "treats_default":with_defaults({"뇌출혈":True})
    },
    "본 서부병원": {
        "lat":37.6050, "lon":126.9090,
        "address":"서울특별시 은평구 은평로 133",
        "treats_default":with_defaults({"심근경색":True})
    },
    "청구 성심 병원": {
        "lat":37.6290, "lon":126.9220,
        "address":"서울특별시 은평구 통일로 873",
        "treats_default":with_defaults({"심근경색":True})
    },
    "성누가병원": {
        "lat":37.6099,"lon":126.9293,
        "address":"서울특별시 은평구 281 102번지",
        "treats_default":with_defaults({"뇌출혈":True})
    },
    "리드힐병원": {
        "lat":37.6203,"lon":126.9299,
        "address":"서울특별시 은평구 연서로 10",
        "treats_default":with_defaults({"기흉":True})
    },
    "연세노블병원": {
        "lat":37.6018,"lon":126.9270,
        "address":"서울특별시 은평구 녹번동 154-19",
        "treats_default":with_defaults({"뇌수막염":True})
    },
}

# ------------------------------------------
# 거리 계산
# ------------------------------------------
def haversine(a,b,c,d):
    R=6371
    dlat=math.radians(c-a)
    dlon=math.radians(d-b)
    A=math.sin(dlat/2)**2 + math.cos(math.radians(a))*math.cos(math.radians(c))*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(A))

def get_route_osrm(lat1,lon1,lat2,lon2):
    url=f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        r=requests.get(url,timeout=4).json()
        route=r["routes"][0]
        coords=route["geometry"]["coordinates"]
        dist=route["distance"]/1000
        eta=route["duration"]/60
        path=[[c[0],c[1]] for c in coords]
        return dist,eta,path
    except:
        d=haversine(lat1,lon1,lat2,lon2)
        return d, d/50*60, [[lon1,lat1],[lon2,lat2]]

# ------------------------------------------
# 세션 초기화
# ------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang="ko"
if "page" not in st.session_state:
    st.session_state.page="home"
if "treats" not in st.session_state:
    st.session_state.treats = {h:info["treats_default"].copy() for h,info in HOSPITALS.items()}

if "start_lat" not in st.session_state:
    st.session_state.start_lat=DEFAULT_LAT
    st.session_state.start_lon=DEFAULT_LON

if "candidate" not in st.session_state:
    st.session_state.candidate=None

# ------------------------------------------
# HOME
# ------------------------------------------
if st.session_state.page=="home":
    st.title(T("app_title"))
    st.caption(T("app_subtitle"))

    st.session_state.lang = st.radio(T("lang_label"),["ko","en"],
        format_func=lambda x:"한국어" if x=="ko" else "English",horizontal=True)

    st.write(T("home_hint"))

    if st.button(T("mode_hospital")):
        st.session_state.page="hospital"
    if st.button(T("mode_ambulance")):
        st.session_state.page="ambulance"

# ------------------------------------------
# 병원 모드
# ------------------------------------------
elif st.session_state.page=="hospital":
    if st.button(T("back_home")):
        st.session_state.page="home"

    st.header(T("hospital_title"))
    st.subheader(T("hospital_step1"))

    hospital=st.selectbox("",list(HOSPITALS.keys()))
    info=HOSPITALS[hospital]

    st.write(T("hospital_check_desc"))
    c1,c2=st.columns(2)
    for i,d in enumerate(DISEASES):
        with (c1 if i%2==0 else c2):
            v=st.checkbox(d,value=st.session_state.treats[hospital][d])
            st.session_state.treats[hospital][d]=v

    st.subheader(T("hospital_step2"))
    st.write(info["address"])

    layer=pdk.Layer("ScatterplotLayer",
        data=[{"lat":info["lat"],"lon":info["lon"]}],
        get_position='[lon,lat]',get_radius=200,get_color=[255,0,0])
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=info["lat"],longitude=info["lon"],zoom=14)
    ))

# ------------------------------------------
# 구급차 모드
# ------------------------------------------
elif st.session_state.page=="ambulance":
    if st.button(T("back_home")):
        st.session_state.page="home"

    st.header(T("ambulance_title"))

    # STEP2
    st.subheader(T("amb_step2"))
    disease = st.radio(T("disease_prompt"), DISEASES, horizontal=True)

    # STEP3
    st.subheader(T("amb_step3"))
    rows=[]
    for h,i in HOSPITALS.items():
        if st.session_state.treats[h][disease]:
            dist,eta,_=get_route_osrm(st.session_state.start_lat,st.session_state.start_lon,i["lat"],i["lon"])
            rows.append({
                "병원":h,"거리(km)":round(dist,2),"시간(분)":round(eta,1),
                "lat":i["lat"],"lon":i["lon"]
            })
    if not rows:
        st.error(T("no_hospital"))
        st.stop()

    df=pd.DataFrame(rows).sort_values("시간(분)").reset_index(drop=True)
    gob=GridOptionsBuilder.from_dataframe(df)
    gob.configure_selection("single",use_checkbox=True)
    grid=AgGrid(df,gridOptions=gob.build(),
                update_mode=GridUpdateMode.SELECTION_CHANGED|GridUpdateMode.MODEL_CHANGED)

    selected=grid["selected_rows"]
    if selected:
        target=selected[0]
    else:
        target=df.iloc[0]

    st.subheader(T("selected_hospital"))
    st.write(target["병원"])
    st.write(HOSPITALS[target["병원"]]["address"])

    # STEP5 지도
    st.subheader(T("amb_step5"))
    dist,eta,path = get_route_osrm(
        st.session_state.start_lat,st.session_state.start_lon,
        target["lat"],target["lon"]
    )
    st.write(T("distance_eta").format(dist=round(dist,2),eta=round(eta,1)))

    # 지도 Layer
    layers=[]
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat":st.session_state.start_lat,"lon":st.session_state.start_lon}],
        get_position='[lon,lat]',get_radius=200,get_color=[0,100,255]
    ))
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=[{"lat":target["lat"],"lon":target["lon"]}],
        get_position='[lon,lat]',get_radius=200,get_color=[255,0,0]
    ))

    # polyline
    line=[{"lon":p[0],"lat":p[1]} for p in path]
    layers.append(pdk.Layer(
        "PathLayer",
        data=[{"path":line}],
        get_path="path",
        get_color=[0,255,0],
        width_scale=20
    ))

    # 지도 클릭 수신
    st.write(T("map_click_hint"))

    click = st.pydeck_chart(pdk.Deck(
        layers=layers,
        map_style=None,
        initial_view_state=pdk.ViewState(
            latitude=(st.session_state.start_lat+target["lat"])/2,
            longitude=(st.session_state.start_lon+target["lon"])/2,
            zoom=13
        ),
        use_container_width=True,
        tooltip={"text":"Click to set start"}
    ))

    # 네이버 지도 URL
    start_lat = st.session_state.start_lat
    start_lon = st.session_state.start_lon
    nav_app = f"nmap://route/car?slat={start_lat}&slng={start_lon}&dlat={target['lat']}&dlng
