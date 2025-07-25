import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# 페이지 기본 설정
st.set_page_config(page_title="📍 나만의 북마크 지도", layout="wide")
st.title("📍 나만의 북마크 지도 (주소 + 삭제 기능 포함)")

# 상태 초기화
if "bookmarks" not in st.session_state:
    st.session_state.bookmarks = []

if "clicked_location" not in st.session_state:
    st.session_state.clicked_location = None

if "clicked_address" not in st.session_state:
    st.session_state.clicked_address = ""

# 지도 생성
m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

# 북마크 마커 표시
for b in st.session_state.bookmarks:
    popup_html = f"""
    <b>{b['name']}</b><br>
    {b['desc']}<br>
    <i>{b['address']}</i>
    """
    folium.Marker(
        [b["lat"], b["lon"]],
        tooltip=b["name"],
        popup=popup_html
    ).add_to(m)

# 지도 표시 및 클릭 감지
clicked_data = st_folium(m, width=1000, height=600)

# 클릭한 좌표 처리
clicked = clicked_data.get("last_clicked") if clicked_data else None

if clicked:
    st.session_state.clicked_location = clicked
    lat = clicked.get("lat")
    lon = clicked.get("lng")

    # 주소 검색 (역지오코딩)
    geolocator = Nominatim(user_agent="bookmark_app")
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)

    try:
        location = reverse((lat, lon), language="ko")
        address = location.address if location else "주소를 찾을 수 없음"
    except:
        address = "주소 검색 실패"

    st.session_state.clicked_address = address

# 📌 북마크 입력
st.sidebar.header("➕ 북마크 추가")

name = st.sidebar.text_input("장소 이름")

lat_val = str(st.session_state.clicked_location["lat"]) if st.session_state.clicked_location else ""
lon_val = str(st.session_state.clicked_location["lng"]) if st.session_state.clicked_location else ""
addr_val = st.session_state.clicked_address or ""

lat = st.sidebar.text_input("위도", value=lat_val)
lon = st.sidebar.text_input("경도", value=lon_val)
addr = st.sidebar.text_area("주소 (자동완성)", value=addr_val, height=60)
desc = st.sidebar.text_area("설명", height=100)

if st.sidebar.button("추가하기"):
    if name and lat and lon:
        try:
            lat = float(lat)
            lon = float(lon)
            st.session_state.bookmarks.append({
                "name": name,
                "lat": lat,
                "lon": lon,
                "address": addr,
                "desc": desc
            })
            st.success(f"✅ '{name}' 장소가 추가되었습니다.")
            st.session_state.clicked_location = None
            st.session_state.clicked_address = ""
            st.rerun()  # ✅ 최신 방식
        except ValueError:
            st.sidebar.error("⚠️ 위도와 경도는 숫자로 입력해주세요.")
    else:
        st.sidebar.error("⚠️ 장소 이름, 위도, 경도를 모두 입력해주세요.")

# 📄 북마크 목록 + 삭제
st.subheader("📌 저장된 북마크 목록")

if st.session_state.bookmarks:
    for i, b in enumerate(st.session_state.bookmarks):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.markdown(f"""
            **{b['name']}**  
            {b['desc']}  
            📍 {b['address']}  
            🧭 ({b['lat']}, {b['lon']})
            """)
        with col2:
            if st.button("❌ 삭제", key=f"delete_{i}"):
                del st.session_state.bookmarks[i]
                st.rerun()  # ✅ 최신 방식
else:
    st.info("아직 북마크가 없습니다. 왼쪽에서 추가해주세요.")
