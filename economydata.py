# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re, io

# ────────────────────────────────────────────
# 0) 페이지 설정 & 용어 설명
# ────────────────────────────────────────────
st.set_page_config(page_title="한국 지역별 EDI 대시보드", layout="wide")
st.markdown("## 📈 한국 지역별 경제발전지수(EDI) 대시보드 · 2021")
with st.expander("ℹ️ 용어 설명"):
    st.markdown("""
- **PPI (Potential Purchasing Index)**  
  : 지역별 **잠재구매력**을 나타내는 지수로, 소득·소비·인구 등을 종합해 산출합니다.  
- **EDI (Economic Development Index)**  
  : 본 대시보드에서는 `EDI = PPI × (가구당 인구수)` 로 정의했습니다.  
    - **가구당 인구수**가 높을수록 소비 잠재력이 커진다고 가정하여 PPI에 가중치를 부여합니다.
""")

# ────────────────────────────────────────────
# 1) CSV 업로드 (정제 버전)
# ────────────────────────────────────────────
st.sidebar.header("CSV 3종 업로드")
pop_file   = st.sidebar.file_uploader("① clean_population.csv",  type="csv")
house_file = st.sidebar.file_uploader("② clean_households.csv", type="csv")
ppi_file   = st.sidebar.file_uploader("③ clean_ppi.csv",        type="csv")

if not (pop_file and house_file and ppi_file):
    st.info("👈  세 CSV 모두 업로드하면 대시보드가 나타납니다.")
    st.stop()

# ────────────────────────────────────────────
# 2) 빠른 CSV 로더 (캐시)
# ────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_csv(upload):
    return pd.read_csv(upload, encoding="utf-8-sig")

pop_df, house_df, ppi_df = load_csv(pop_file), load_csv(house_file), load_csv(ppi_file)

# ────────────────────────────────────────────
# 3) 시·도(광역 단위) 추출 함수
# ────────────────────────────────────────────
CANON = {
    "서울특별시": "서울특별시", "부산광역시": "부산광역시", "대구광역시": "대구광역시",
    "인천광역시": "인천광역시", "광주광역시": "광주광역시", "대전광역시": "대전광역시",
    "울산광역시": "울산광역시", "세종특별자치시": "세종특별자치시",
    "경기도": "경기도", "강원도": "강원도",
    "충청북도": "충청북도", "충청남도": "충청남도",
    "전라북도": "전라북도", "전라남도": "전라남도",
    "경상북도": "경상북도", "경상남도": "경상남도",
    "제주특별자치도": "제주특별자치도",
}

def extract_province(region: str) -> str:
    """서울특별시노원구 → 서울특별시  |  경기도수원시 → 경기도"""
    for canon in CANON:
        if region.startswith(canon):
            return canon
    return region  # 예외(드물게 정제 안 된 경우)

# ────────────────────────────────────────────
# 4) 병합 & 지표 계산
# ────────────────────────────────────────────
df = (pop_df.merge(house_df, on="region", how="inner")
             .merge(ppi_df,   on="region", how="inner"))

if df.empty:
    st.error("❌ 공통 region 이 없습니다. 파일 확인!")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]
df["province"] = df["region"].apply(extract_province)

# ────────────────────────────────────────────
# 5) 시·도 단위 필터 (멀티셀렉트)
# ────────────────────────────────────────────
provinces_all = sorted(df["province"].unique())
sel_provinces = st.sidebar.multiselect(
    "🔎 시·도 선택 (미선택=전체)", provinces_all, default=provinces_all
)
df = df[df["province"].isin(sel_provinces)] if sel_provinces else df

# ------------- 지역 리스트 (시군구) -------------
regions_filtered = df["region"].tolist()
sel_regions = st.sidebar.multiselect(
    "세부 지역(시·군·구) 선택 (미선택=전부)", regions_filtered, default=regions_filtered
)
df = df[df["region"].isin(sel_regions)] if sel_regions else df

# ────────────────────────────────────────────
# 6) 뷰 선택 + 그래프
# ────────────────────────────────────────────
view = st.sidebar.radio("보기", ["지표 막대", "EDI 막대", "인구·세대 막대"])

if view == "지표 막대":
    st.subheader("📊 지역별 주요 지표")
    long = df.melt(
        id_vars=["region"], value_vars=["total_population", "households", "PPI", "people_per_house", "EDI"],
        var_name="metric", value_name="value"
    )
    fig = px.bar(long, x="region", y="value", color="metric",
                 barmode="group",
                 labels={"value":"값","metric":"지표","region":"지역"},
                 height=550)
    st.plotly_chart(fig, use_container_width=True)

elif view == "EDI 막대":
    st.subheader("🏆 EDI 순위 (막대그래프)")
    fig = px.bar(df.sort_values("EDI", ascending=False),
                 x="EDI", y="region", orientation="h",
                 labels={"EDI":"경제발전지수(EDI)","region":"지역"},
                 height=600)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.subheader("👥 총인구 & 세대수")
    fig = px.bar(df.sort_values("total_population", ascending=False),
                 x="region", y=["total_population", "households"],
                 barmode="group",
                 labels={"value":"명 / 세대","variable":"지표","region":"지역"},
                 height=550)
    st.plotly_chart(fig, use_container_width=True)

# ────────────────────────────────────────────
# 7) 다운 버튼 (메모리 그대로, 추가 I/O X)
# ────────────────────────────────────────────
st.sidebar.header("정제 CSV 다운로드")
for name, file in [("clean_population.csv", pop_file),
                   ("clean_households.csv", house_file),
                   ("clean_ppi.csv",       ppi_file)]:
    st.sidebar.download_button(name + " 📥", file.getvalue(), name)
