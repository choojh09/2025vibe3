# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import io

# ─────────────────────────────────────────────
# 0) 페이지·용어 설정
# ─────────────────────────────────────────────
st.set_page_config(page_title="시·도별 EDI 대시보드", layout="wide")
st.markdown("## 🚀 시·도별 경제발전지수(EDI) 대시보드 · 2021")

with st.expander("ℹ️ 용어 설명"):
    st.markdown("""
- **PPI (Potential Purchasing Index)**  
  : 각 시·도의 **잠재구매력**을 나타내는 지수입니다.  
- **EDI (Economic Development Index)**  
  : 본 대시보드에서는 `EDI = PPI × (총인구 ÷ 세대수)` 로 간단히 산출했습니다.  
    - 가구당 인구수가 높을수록 소비 잠재력이 커진다는 가정입니다.
""")

# ─────────────────────────────────────────────
# 1) 정제 CSV 업로드
# ─────────────────────────────────────────────
st.sidebar.header("정제 CSV 업로드")
pop_file   = st.sidebar.file_uploader("① highlevel_population.csv",  type="csv")
house_file = st.sidebar.file_uploader("② highlevel_households.csv", type="csv")
ppi_file   = st.sidebar.file_uploader("③ highlevel_ppi.csv",        type="csv")

if not (pop_file and house_file and ppi_file):
    st.info("👈  세 CSV를 모두 업로드하면 대시보드가 나타납니다.")
    st.stop()

# ─────────────────────────────────────────────
# 2) 빠른 CSV 로딩 (캐시)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def read_csv(upload):
    return pd.read_csv(upload, encoding="utf-8-sig")

pop_df   = read_csv(pop_file)      # region, total_population
house_df = read_csv(house_file)    # region, households
ppi_df   = read_csv(ppi_file)      # region, PPI

# ─────────────────────────────────────────────
# 3) 병합 & 지표 계산
# ─────────────────────────────────────────────
df = (pop_df.merge(house_df, on="region", how="inner")
             .merge(ppi_df,   on="region", how="inner"))

if df.empty:
    st.error("❌ 파일 간 공통 region 이 없습니다. 다시 확인해 주세요.")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ─────────────────────────────────────────────
# 4) 시·도 필터 (멀티셀렉트)
# ─────────────────────────────────────────────
provinces = df["region"].tolist()          # 이미 17개 시·도만 있음
sel = st.sidebar.multiselect("🔎 시·도 선택 (미선택 = 전체)", provinces, default=provinces)
df_view = df[df["region"].isin(sel)] if sel else df

# ─────────────────────────────────────────────
# 5) 뷰 선택 + 그래프
# ─────────────────────────────────────────────
view = st.sidebar.radio("보기", ["지표 막대", "EDI 순위", "인구·세대 막대"])

if view == "지표 막대":
    st.subheader("📊 시·도별 주요 지표")
    long = df_view.melt(
        id_vars="region",
        value_vars=["total_population", "households", "PPI", "people_per_house", "EDI"],
        var_name="metric", value_name="value",
    )
    fig = px.bar(
        long, x="region", y="value", color="metric", barmode="group",
        labels={"value": "값", "metric": "지표", "region": "시·도"},
        height=550,
    )
    st.plotly_chart(fig, use_container_width=True)

elif view == "EDI 순위":
    st.subheader("🏆 경제발전지수(EDI) 순위")
    fig = px.bar(
        df_view.sort_values("EDI", ascending=False),
        x="EDI", y="region", orientation="h",
        labels={"EDI": "EDI", "region": "시·도"},
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.subheader("👥 총인구 & 세대수")
    fig = px.bar(
        df_view.sort_values("total_population", ascending=False),
        x="region", y=["total_population", "households"],
        barmode="group",
        labels={"value": "명 / 세대", "variable": "지표", "region": "시·도"},
        height=550,
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# 6) 원본 정제 CSV 다시 다운로드 (선택 사항)
# ─────────────────────────────────────────────
st.sidebar.header("정제 CSV 다운로드")
for lbl, upl in [("highlevel_population.csv", pop_file),
                 ("highlevel_households.csv", house_file),
                 ("highlevel_ppi.csv",       ppi_file)]:
    st.sidebar.download_button(lbl + " 📥", upl.getvalue(), lbl)
