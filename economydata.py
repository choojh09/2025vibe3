# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# ──────────────────────────────────────────
# 0) 페이지 기본 설정
# ──────────────────────────────────────────
st.set_page_config(page_title="지역별 경제전망 대시보드", layout="wide")
st.title("📈 지역별 경제발전·주거지표 대시보드 (2021)")

# ──────────────────────────────────────────
# 1) CSV 업로드 (정제 버전 3종)
# ──────────────────────────────────────────
st.sidebar.header("정제 CSV 업로드")
pop_file  = st.sidebar.file_uploader("① 인구 (clean_population.csv)",  type="csv")
house_file= st.sidebar.file_uploader("② 세대수 (clean_households.csv)", type="csv")
ppi_file  = st.sidebar.file_uploader("③ PPI (clean_ppi.csv)",          type="csv")

if not (pop_file and house_file and ppi_file):
    st.info("👈 좌측에서 3 개 정제 CSV를 모두 업로드하면 대시보드가 나타납니다.")
    st.stop()

# ──────────────────────────────────────────
# 2) 데이터 로드
# ──────────────────────────────────────────
def load_csv(upload):
    return pd.read_csv(upload, encoding="utf-8-sig")

pop_df   = load_csv(pop_file)   # region, total_population
house_df = load_csv(house_file) # region, households
ppi_df   = load_csv(ppi_file)   # region, PPI

# ──────────────────────────────────────────
# 3) 병합 & 지표 계산
# ──────────────────────────────────────────
df = (
    pop_df.merge(house_df, on="region", how="inner")
           .merge(ppi_df,   on="region", how="inner")
)

if df.empty:
    st.error("❌ 세 파일 간에 공통 region 이 없습니다. 정제 단계 다시 확인!")
    st.stop()

# ▶︎ 경제발전지수(EDI)  = PPI × (가구 당 인구)   ←  간단 예시
df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ──────────────────────────────────────────
# 4) 대시보드 뷰 선택
# ──────────────────────────────────────────
view = st.sidebar.radio("보기", ["지역별 표", "EDI 산점도", "인구 피라미드"])

if view == "지역별 표":
    st.subheader("📋 지역별 요약")
    st.dataframe(
        df.sort_values("EDI", ascending=False)
          .reset_index(drop=True),
        use_container_width=True
    )

elif view == "EDI 산점도":
    st.subheader("🔍 인구·세대 × PPI")
    fig = px.scatter(
        df, x="people_per_house", y="EDI",
        size="total_population", text="region",
        labels={
            "people_per_house": "가구당 인구수",
            "EDI": "경제발전지수(EDI)",
            "total_population": "총인구"
        }
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

else:  # 인구 피라미드
    # 업로드된 인구 CSV에는 연령 구간별 세부 컬럼이 들어 있지 않고
    # total_population 만 있으므로 간단 예시로 막대그래프 제공
    st.subheader("📊 지역별 총인구 & 세대수")
    fig = px.bar(
        df.sort_values("total_population", ascending=False),
        x="region", y=["total_population", "households"],
        barmode="group",
        labels={"value":"명 / 세대", "variable":"지표", "region":"지역"}
    )
    st.plotly_chart(fig, use_container_width=True)

# ──────────────────────────────────────────
# 5) 다운로드용 CSV 다시 제공 (옵션)
# ──────────────────────────────────────────
st.sidebar.header("정제 파일 다시 받기")
st.sidebar.download_button(
    "clean_population.csv 📥", pop_file.getvalue(), "clean_population.csv"
)
st.sidebar.download_button(
    "clean_households.csv 📥", house_file.getvalue(), "clean_households.csv"
)
st.sidebar.download_button(
    "clean_ppi.csv 📥", ppi_file.getvalue(), "clean_ppi.csv"
)
