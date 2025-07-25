# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# ─────────────────────────────
# 0. 기본
# ─────────────────────────────
st.set_page_config(page_title="지역별 EDI 대시보드", layout="wide")
st.title("📈 지역별 경제발전지수(EDI) 대시보드 · 2021")

# ─────────────────────────────
# 1. 정제 CSV 업로드
# ─────────────────────────────
st.sidebar.header("정제 CSV 3종 업로드")
pop_file   = st.sidebar.file_uploader("① clean_population.csv",  type="csv")
house_file = st.sidebar.file_uploader("② clean_households.csv", type="csv")
ppi_file   = st.sidebar.file_uploader("③ clean_ppi.csv",        type="csv")

if not (pop_file and house_file and ppi_file):
    st.info("👈 세 정제 CSV를 모두 업로드해 주세요.")
    st.stop()

load = lambda f: pd.read_csv(f, encoding="utf-8-sig")
pop_df   = load(pop_file)      # region, total_population
house_df = load(house_file)    # region, households
ppi_df   = load(ppi_file)      # region, PPI

# ─────────────────────────────
# 2. 병합 & 지표
# ─────────────────────────────
df = (
    pop_df.merge(house_df, on="region", how="inner")
          .merge(ppi_df,   on="region", how="inner")
)

if df.empty:
    st.error("❌ 공통 region 이 없습니다. 파일 확인!")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ─────────────────────────────
# 3. 지역 필터
# ─────────────────────────────
all_regions = df["region"].tolist()
sel_regions = st.sidebar.multiselect(
    "🔎 보고 싶은 지역 선택 (미선택 → 전체)", all_regions, default=all_regions
)
if sel_regions:
    df = df[df["region"].isin(sel_regions)]

# ─────────────────────────────
# 4. 대시보드 뷰
# ─────────────────────────────
view = st.sidebar.radio("보기", ["시각화된 표", "EDI 산점도", "인구·세대 막대"])

# ---- 4‑1. 시각화된 표 ----
if view == "시각화된 표":
    st.subheader("📋 지역별 지표 (선택 지역)")
    fig_tbl = go.Figure(
        data=[go.Table(
            header=dict(values=list(df.columns),
                        fill_color="#506784", font_color="white", align="center"),
            cells=dict(values=[df[c] for c in df.columns],
                       fill_color="#F5F8FF", align="center"))
        ]
    )
    st.plotly_chart(fig_tbl, use_container_width=True)

# ---- 4‑2. EDI 산점도 ----
elif view == "EDI 산점도":
    st.subheader("🔍 EDI × 가구당 인구수 (선택 지역)")
    fig = px.scatter(
        df,
        x="people_per_house",
        y="EDI",
        size="total_population",
        text="region",
        labels={
            "people_per_house": "가구당 인구수",
            "EDI": "경제발전지수(EDI)",
            "total_population": "총인구",
        },
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

# ---- 4‑3. 인구·세대 막대 ----
else:
    st.subheader("📊 총인구 & 세대수 (선택 지역)")
    fig = px.bar(
        df.sort_values("total_population", ascending=False),
        x="region",
        y=["total_population", "households"],
        barmode="group",
        labels={"value": "명 / 세대", "variable": "지표", "region": "지역"},
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────
# 5. 다시 다운로드 버튼
# ─────────────────────────────
st.sidebar.header("정제 CSV 다운로드")
for name, upl in zip(
    ["clean_population.csv", "clean_households.csv", "clean_ppi.csv"],
    [pop_file, house_file, ppi_file],
):
    st.sidebar.download_button(f"{name} 📥", upl.getvalue(), name)
