import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="📍 나만의 북마크 지도", layout="wide")
st.title("📍 나만의 북마크 지도")

# 북마크 초기화
if 'bookmarks' not in st.session_state:
    st.session_state.bookmarks = []

# 📌 북마크 입력
with st.sidebar:
    st.header("➕ 북마크 추가")
    name = st.text_input("장소 이름")
    lat = st.text_input("위도 (예: 37.5665)")
    lon = st.text_input("경도 (예: 126.9780)")
    desc = st.text_area("설명", height=100)
    add_btn = st.button("추가하기")

    if add_btn:
        if name and lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)
                st.session_state.bookmarks.append({
                    "name": name,
                    "lat": lat,
                    "lon": lon,
                    "desc": desc
                })
                st.success(f"'{name}' 장소가 지도에 추가되었습니다.")
            except ValueError:
                st.error("위도와 경도는 숫자로 입력해주세요.")
        else:
            st.error("장소 이름, 위도, 경도를 모두 입력해주세요.")

# 🌏 지도 생성
m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

# 북마크 마커 추가
for b in st.session_state.bookmarks:
    folium.Marker(
        [b["lat"], b["lon"]],
        tooltip=b["name"],
        popup=f"<b>{b['name']}</b><br>{b['desc']}"
    ).add_to(m)

# 지도 표시
st_data = st_folium(m, width=1000, height=600)

# 📄 북마크 목록 표시
if st.session_state.bookmarks:
    st.subheader("📌 저장된 북마크 목록")
    df = pd.DataFrame(st.session_state.bookmarks)
    st.dataframe(df[["name", "lat", "lon", "desc"]], use_container_width=True)
else:
    st.info("아직 북마크가 없습니다. 왼쪽에서 추가해주세요.")
