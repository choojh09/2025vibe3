# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import io

# ─────────────────────────────
# 0. 페이지 기본
# ─────────────────────────────
st.set_page_config(page_title="지역별 EDI 대시보드", layout="wide")
st.title("📈 지역별 경제발전지수(EDI) 대시보드 · 2021")

# ─────────────────────────────
# 1. CSV 업로드
# ─────────────────────────────
st.sidebar.header("정제 CSV 3종 업로드")
pop_file   = st.sidebar.file_uploader("① clean_population.csv",  type="csv")
house_file = st.sidebar.file_uploader("② clean_households.csv", type="csv")
ppi_file   = st.sidebar.file_uploader("③ clean_ppi.csv",        type="csv")

if not (pop_file and house_file and ppi_file):
    st.info("👈 세 정제 CSV를 모두 업로드하면 대시보드가 나타납니다.")
    st.stop()

read_csv = lambda f: pd.read_csv(f, encoding="utf-8-sig")
pop_df, house_df, ppi_df = map(read_csv, [pop_file, house_file, ppi_file])

# ─────────────────────────────
# 2. 병합 & 지표
# ─────────────────────────────
df = (pop_df.merge(house_df, on="region", how="inner")
             .merge(ppi_df,   on="region", how="inner"))

if df.empty:
    st.error("❌ 공통 region 이 없습니다.")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ─────────────────────────────
# 3. 지역 필터
# ─────────────────────────────
regions_all = df["region"].tolist()
sel_regions = st.sidebar.multiselect("🔍 지역 선택 (미선택=전체)", regions_all, default=regions_all)
df = df[df["region"].isin(sel_regions)] if sel_regions else df

# ─────────────────────────────
# 4. 뷰 선택
# ─────────────────────────────
view = st.sidebar.radio("보기", ["지표 막대그래프", "EDI 막대그래프", "인구·세대 막대그래프"])

# ---- 4‑1. 모든 지표 막대그래프 ----
if view == "지표 막대그래프":
    st.subheader("📊 지역별 주요 지표 막대그래프")
    long_df = df.melt(id_vars="region",
                      value_vars=["total_population", "households", "PPI", "people_per_house", "EDI"],
                      var_name="metric", value_name="value")
    fig = px.bar(long_df, x="region", y="value", color="metric",
                 barmode="group", height=600,
                 labels={"value":"값", "metric":"지표", "region":"지역"})
    st.plotly_chart(fig, use_container_width=True)

# ---- 4‑2. EDI 막대그래프 ----
elif view == "EDI 막대그래프":
    st.subheader("🏆 EDI 순위 (막대그래프)")
    fig = px.bar(df.sort_values("EDI", ascending=False),
                 x="EDI", y="region", orientation="h",
                 labels={"EDI":"경제발전지수(EDI)", "region":"지역"}, height=600)
    st.plotly_chart(fig, use_container_width=True)

# ---- 4‑3. 인구·세대 막대그래프 ----
else:
    st.subheader("👥 총인구 & 세대수")
    fig = px.bar(df.sort_values("total_population", ascending=False),
                 x="region", y=["total_population", "households"],
                 barmode="group",
                 labels={"value":"명 / 세대", "variable":"지표", "region":"지역"},
                 height=600)
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────
# 5. 정제 CSV 다운로드 (옵션)
# ─────────────────────────────
st.sidebar.header("정제 CSV 다운로드")
for lbl, upl in [("clean_population.csv", pop_file),
                 ("clean_households.csv", house_file),
                 ("clean_ppi.csv", ppi_file)]:
    st.sidebar.download_button(lbl + " 📥", upl.getvalue(), lbl)
