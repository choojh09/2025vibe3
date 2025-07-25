# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re, io

# ────────────────────────────────────────────
# 0) 기본 설정 & 용어 설명
# ────────────────────────────────────────────
st.set_page_config(page_title="시·도별 EDI 대시보드", layout="wide")
st.markdown("## 🚀 시·도별 경제발전지수(EDI) 대시보드 · 2021")

with st.expander("ℹ️ 용어 설명"):
    st.markdown("""
- **PPI (Potential Purchasing Index)**  
  : 시·도의 **잠재구매력**을 나타내는 복합 지수입니다.  
- **EDI (Economic Development Index)**  
  : 본 대시보드에서는 `EDI = PPI × (총인구 ÷ 세대수)` 로 정의했습니다.  
    - 가구당 인구수가 높을수록 소비 잠재력이 커진다는 단순 가정.  
- **미래 전망 시뮬레이션**  
  : PPI 성장률·가구당 인구수 변화율을 가정해 **N 년 뒤 EDI** 를 예측합니다.
""")

# ────────────────────────────────────────────
# 1) 정제 CSV 업로드
# ────────────────────────────────────────────
st.sidebar.header("정제 CSV 업로드")
pop_file   = st.sidebar.file_uploader("① aligned_population.csv",  type="csv")
house_file = st.sidebar.file_uploader("② aligned_households.csv", type="csv")
ppi_file   = st.sidebar.file_uploader("③ aligned_ppi_fixed.csv",  type="csv")

if not (pop_file and house_file and ppi_file):
    st.info("👈  좌측에서 3 개 CSV를 모두 업로드해 주세요.")
    st.stop()

# ────────────────────────────────────────────
# 2) 캐싱된 CSV 로더
# ────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_csv(upload):
    return pd.read_csv(upload, encoding="utf-8-sig")

pop_df   = load_csv(pop_file)    # region, total_population
house_df = load_csv(house_file)  # region, households
ppi_df   = load_csv(ppi_file)    # region, PPI

# ────────────────────────────────────────────
# 3) 병합 & EDI 계산
# ────────────────────────────────────────────
df = (
    pop_df.merge(house_df, on="region", how="inner")
          .merge(ppi_df,   on="region", how="inner")
)
if df.empty:
    st.error("❌ 세 파일 간 `region` 값이 맞지 않습니다.")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ────────────────────────────────────────────
# 4) 시·도 필터 (17개 고정)
# ────────────────────────────────────────────
provinces = df["region"].tolist()        # 이미 광역만 있음
sel_prov  = st.sidebar.multiselect(
    "🔎 시·도 선택 (미선택 = 전체)", provinces, default=provinces
)
df_view = df[df["region"].isin(sel_prov)] if sel_prov else df

# ────────────────────────────────────────────
# 5) 뷰 선택
# ────────────────────────────────────────────
view = st.sidebar.radio(
    "보기",
    ["지표 막대", "EDI 순위", "인구·세대 막대", "미래 전망 ▸"]
)

# ---------- 5‑1. 지표 막대 ----------
if view == "지표 막대":
    st.subheader("📊 시·도별 주요 지표")
    long = df_view.melt(
        id_vars="region",
        value_vars=["total_population", "households", "PPI", "people_per_house", "EDI"],
        var_name="metric", value_name="value"
    )
    fig = px.bar(
        long, x="region", y="value", color="metric",
        barmode="group",
        labels={"value":"값","metric":"지표","region":"시·도"},
        height=550
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5‑2. EDI 순위 ----------
elif view == "EDI 순위":
    st.subheader("🏆 EDI 순위 (가로 막대)")
    fig = px.bar(
        df_view.sort_values("EDI", ascending=False),
        x="EDI", y="region", orientation="h",
        labels={"EDI":"경제발전지수(EDI)","region":"시·도"},
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5‑3. 인구·세대 ----------
elif view == "인구·세대 막대":
    st.subheader("👥 총인구 & 세대수")
    fig = px.bar(
        df_view.sort_values("total_population", ascending=False),
        x="region", y=["total_population", "households"],
        barmode="group",
        labels={"value":"명 / 세대","variable":"지표","region":"시·도"},
        height=550
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5‑4. 미래 전망 ----------
else:
    st.subheader("🚀 미래 EDI 시뮬레이션")

    c1, c2, c3 = st.columns(3)
    with c1:
        yrs = st.number_input("몇 년 뒤?", 1, 30, value=5, step=1)
    with c2:
        g_ppi = st.slider("PPI 연 성장률(%)", -5.0, 10.0, 1.5, 0.1)
    with c3:
        g_pph = st.slider("가구당 인구수 연 변화율(%)", -3.0, 3.0, -0.5, 0.1)

    df_proj = df_view.copy()
    df_proj["EDI_future"] = (
        df_proj["EDI"]
        * (1 + g_ppi / 100) ** yrs
        * (1 + g_pph / 100) ** yrs
    )

    st.markdown(f"#### 📈 {yrs}년 뒤 예상 EDI")
    fig = px.bar(
        df_proj.sort_values("EDI_future", ascending=False),
        x="EDI_future", y="region", orientation="h",
        labels={"EDI_future": f"EDI (+{g_ppi}% & {g_pph}% /y)", "region": "시·도"},
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("🔍 계산식 / 가정"):
        st.markdown(f"""
- **계산식**  
  `EDI_future = EDI × (1 + g_PPI)^t × (1 + g_PPH)^t`  
  - *g_PPI*: PPI 연평균 성장률  
  - *g_PPH*: 가구당 인구수 연평균 변화율  
  - *t*: {yrs} 년
- 실제 경제 상황에 따라 달라질 수 있는 **단순 시나리오 분석**입니다.
""")

# ────────────────────────────────────────────
# 6) CSV 다시 다운로드
# ────────────────────────────────────────────
st.sidebar.header("정제 CSV 다운로드")
for fname, upl in [("aligned_population.csv", pop_file),
                   ("aligned_households.csv", house_file),
                   ("aligned_ppi_fixed.csv", ppi_file)]:
    st.sidebar.download_button(fname + " 📥", upl.getvalue(), fname)
