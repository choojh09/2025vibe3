# app.py
import streamlit as st, pandas as pd, plotly.express as px, numpy as np, re, io

st.set_page_config(page_title="시·도별 EDI 대시보드", layout="wide")
st.markdown("## 🚀 시·도별 경제발전지수(EDI) 대시보드 · 2021")

# ─────────────────────────────
# 0. CSV 업로드
# ─────────────────────────────
st.sidebar.header("정제 CSV 업로드")
pop_upl   = st.sidebar.file_uploader("① aligned_population.csv",  type="csv")
house_upl = st.sidebar.file_uploader("② aligned_households.csv", type="csv")
ppi_upl   = st.sidebar.file_uploader("③ aligned_ppi_fixed.csv",  type="csv")
if not (pop_upl and house_upl and ppi_upl):
    st.info("👈 세 CSV 업로드 후 대시보드가 나타납니다.")
    st.stop()

@st.cache_data(show_spinner=False)
def read_csv(u): return pd.read_csv(u, encoding="utf-8-sig")

pop_raw, house_raw, ppi_raw = map(read_csv, [pop_upl, house_upl, ppi_upl])

# ─────────────────────────────
# 1. 컬럼 자동 탐색 & 표준화
# ─────────────────────────────
def col_like(df, patterns):
    for p in patterns:
        for c in df.columns:
            if re.search(p, c, re.I):
                return c
    return None

# 인구
reg_col_pop = col_like(pop_raw, ["region", "지역", "행정"]) or pop_raw.columns[0]
pop_col     = col_like(pop_raw, ["total", "인구", "population"]) or pop_raw.columns[-1]
pop_df = pop_raw[[reg_col_pop, pop_col]].rename(
    columns={reg_col_pop: "region", pop_col: "total_population"}
)

# 세대수
reg_col_house = col_like(house_raw, ["region", "지역", "행정"]) or house_raw.columns[0]
house_col     = col_like(house_raw, ["house", "세대"]) or house_raw.columns[-1]
house_df = house_raw[[reg_col_house, house_col]].rename(
    columns={reg_col_house: "region", house_col: "households"}
)

# PPI
reg_col_ppi = col_like(ppi_raw, ["region", "지역", "행정"]) or ppi_raw.columns[0]
ppi_col     = col_like(ppi_raw, ["PPI", "구매", "index", "지수"]) or ppi_raw.columns[-1]
ppi_df = ppi_raw[[reg_col_ppi, ppi_col]].rename(
    columns={reg_col_ppi: "region", ppi_col: "PPI"}
)

# 숫자형 변환
for c in ["total_population", "households", "PPI"]:
    if c in pop_df:  pop_df[c]  = pd.to_numeric(pop_df[c],  errors="coerce")
    if c in house_df: house_df[c]= pd.to_numeric(house_df[c],errors="coerce")
    if c in ppi_df:   ppi_df[c]  = pd.to_numeric(ppi_df[c], errors="coerce")

# ─────────────────────────────
# 2. 병합 & EDI
# ─────────────────────────────
df = (pop_df.merge(house_df, on="region", how="inner")
             .merge(ppi_df,   on="region", how="inner"))
df = df.dropna(subset=["total_population","households","PPI"])
if df.empty:
    st.error("❌ 세 파일의 region 값이 서로 다릅니다.")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ─────────────────────────────
# 3. 필터
# ─────────────────────────────
regions = df["region"].tolist()
sel = st.sidebar.multiselect("시·도 선택", regions, default=regions)
df = df[df["region"].isin(sel)] if sel else df

# ─────────────────────────────
# 4. 뷰 선택
# ─────────────────────────────
view = st.sidebar.radio("보기", ["EDI 순위", "지표 막대", "미래 전망"])

if view == "EDI 순위":
    st.subheader("🏆 EDI 순위")
    fig = px.bar(df.sort_values("EDI", ascending=False),
                 x="EDI", y="region", orientation="h",
                 labels={"EDI":"EDI","region":"시·도"}, height=600)
    st.plotly_chart(fig, use_container_width=True)

elif view == "지표 막대":
    st.subheader("📊 주요 지표")
    long = df.melt(id_vars="region",
                   value_vars=["total_population","households","PPI","people_per_house","EDI"],
                   var_name="metric", value_name="value")
    fig = px.bar(long, x="region", y="value", color="metric",
                 barmode="group", height=550,
                 labels={"value":"값","metric":"지표","region":"시·도"})
    st.plotly_chart(fig, use_container_width=True)

else:
    st.subheader("🚀 미래 EDI 시뮬레이션")
    yrs  = st.number_input("N 년 뒤", 1, 30, 5)
    g_ppi= st.slider("PPI 연 성장률(%)", -5.0, 10.0, 1.5, 0.1)
    g_pph= st.slider("가구당 인구 연 변화율(%)", -3.0, 3.0, -0.5, 0.1)

    df_future = df.copy()
    df_future["EDI_future"] = (
        df_future["EDI"] * (1+g_ppi/100)**yrs * (1+g_pph/100)**yrs
    )
    fig = px.bar(df_future.sort_values("EDI_future", ascending=False),
                 x="EDI_future", y="region", orientation="h",
                 labels={"EDI_future":f"EDI(+{g_ppi}%·{g_pph}%/y, {yrs}y)",
                         "region":"시·도"},
                 height=600)
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────
# 5. 다운로드 (옵션)
# ─────────────────────────────
st.sidebar.header("원본 CSV 다운로드")
for lbl, upl in [("aligned_population.csv", pop_upl),
                 ("aligned_households.csv", house_upl),
                 ("aligned_ppi_fixed.csv", ppi_upl)]:
    st.sidebar.download_button(lbl+" 📥", upl.getvalue(), lbl)
