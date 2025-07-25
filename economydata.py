# app.py
import streamlit as st, pandas as pd, plotly.express as px, numpy as np, re

# ──────────────────────────────────────────
# 0. 기본 / 용어
# ──────────────────────────────────────────
st.set_page_config(page_title="시·도 EDI 대시보드", layout="wide")
st.markdown("## 🚀 시·도별 경제발전지수(EDI) 대시보드 · 2021")

with st.expander("ℹ️ 용어"):
    st.markdown("""
- **PPI**: 잠재구매력지수  
- **EDI**: `PPI × (총인구 ÷ 세대수)`  
- **미래 전망**: 연 성장률·변화율을 가정해 `N`년 뒤 EDI 예측  
- **주관적 평가**: 현재 EDI를 상·중·하 3등급으로 자동 분류 + 간략 해석
""")

# ──────────────────────────────────────────
# 1. CSV 업로드
# ──────────────────────────────────────────
st.sidebar.header("정제 CSV 업로드")
pop_upl   = st.sidebar.file_uploader("① aligned_population.csv",  type="csv")
house_upl = st.sidebar.file_uploader("② aligned_households.csv", type="csv")
ppi_upl   = st.sidebar.file_uploader("③ aligned_ppi_fixed.csv",  type="csv")
if not (pop_upl and house_upl and ppi_upl):
    st.info("👈 세 CSV를 모두 업로드하면 대시보드가 나타납니다.")
    st.stop()

@st.cache_data(show_spinner=False)
def read_csv(u): return pd.read_csv(u, encoding="utf-8-sig")

pop_raw, house_raw, ppi_raw = map(read_csv, [pop_upl, house_upl, ppi_upl])

# ──────────────────────────────────────────
# 2. 컬럼 자동 탐색·표준화
# ──────────────────────────────────────────
def col_like(df, pats):
    return next((c for p in pats for c in df.columns if re.search(p, c, re.I)), None)

# 인구
rc_pop = col_like(pop_raw, ["region","지역","행정"]) or pop_raw.columns[0]
pc_pop = col_like(pop_raw, ["total","인구","population"]) or pop_raw.columns[-1]
pop_df = pop_raw[[rc_pop, pc_pop]].rename(columns={rc_pop:"region", pc_pop:"total_population"})

# 세대
rc_house = col_like(house_raw, ["region","지역","행정"]) or house_raw.columns[0]
pc_house = col_like(house_raw, ["house","세대"]) or house_raw.columns[-1]
house_df = house_raw[[rc_house, pc_house]].rename(columns={rc_house:"region", pc_house:"households"})

# PPI
rc_ppi = col_like(ppi_raw, ["region","지역","행정"]) or ppi_raw.columns[0]
pc_ppi = col_like(ppi_raw, ["ppi","구매","index","지수"]) or ppi_raw.columns[-1]
ppi_df = ppi_raw[[rc_ppi, pc_ppi]].rename(columns={rc_ppi:"region", pc_ppi:"PPI"})

# 숫자형
for df in [pop_df, house_df, ppi_df]:
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# ──────────────────────────────────────────
# 3. 병합 & EDI
# ──────────────────────────────────────────
df = (pop_df.merge(house_df, on="region", how="inner")
             .merge(ppi_df,   on="region", how="inner")).dropna()

if df.empty:
    st.error("❌ 세 파일의 region 값이 일치하지 않습니다.")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ──────────────────────────────────────────
# 4. 시·도 필터
# ──────────────────────────────────────────
regions = df["region"].tolist()
sel = st.sidebar.multiselect("시·도 선택", regions, default=regions)
df_view = df[df["region"].isin(sel)] if sel else df

# ──────────────────────────────────────────
# 5. 뷰 선택
# ──────────────────────────────────────────
view = st.sidebar.radio(
    "보기",
    ["EDI 순위", "지표 막대", "인구·세대 막대", "미래 전망", "주관적 평가"]
)

# ---------- 5‑1. EDI 순위 ----------
if view == "EDI 순위":
    st.subheader("🏆 EDI 순위")
    fig = px.bar(df_view.sort_values("EDI", ascending=False),
                 x="EDI", y="region", orientation="h",
                 labels={"EDI":"EDI","region":"시·도"}, height=600)
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5‑2. 지표 막대 ----------
elif view == "지표 막대":
    st.subheader("📊 주요 지표")
    long = df_view.melt(id_vars="region",
                 value_vars=["total_population","households","PPI","people_per_house","EDI"],
                 var_name="metric", value_name="value")
    fig = px.bar(long, x="region", y="value", color="metric",
                 barmode="group", height=550,
                 labels={"value":"값","metric":"지표","region":"시·도"})
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5‑3. 인구·세대 ----------
elif view == "인구·세대 막대":
    st.subheader("👥 총인구 & 세대수")
    fig = px.bar(df_view.sort_values("total_population", ascending=False),
                 x="region", y=["total_population","households"],
                 barmode="group", height=550,
                 labels={"value":"명 / 세대","variable":"지표","region":"시·도"})
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5‑4. 미래 전망 ----------
elif view == "미래 전망":
    st.subheader("🚀 미래 EDI 시뮬레이션")
    c1,c2,c3 = st.columns(3)
    yrs  = c1.number_input("N 년 뒤", 1, 30, 5)
    g_ppi= c2.slider("PPI 연 성장률(%)", -5.0, 10.0, 1.5, 0.1)
    g_pph= c3.slider("가구당 인구 연 변화율(%)",-3.0, 3.0, -0.5, 0.1)

    df_future = df_view.copy()
    df_future["EDI_future"] = (
        df_future["EDI"]*(1+g_ppi/100)**yrs*(1+g_pph/100)**yrs
    )
    fig = px.bar(df_future.sort_values("EDI_future", ascending=False),
                 x="EDI_future", y="region", orientation="h",
                 labels={"EDI_future":f"EDI(+{g_ppi}%·{g_pph}%/y, {yrs}y)","region":"시·도"},
                 height=600)
    st.plotly_chart(fig, use_container_width=True)

# ---------- 5‑5. 주관적 평가 ----------
else:
    st.subheader("📝 주관적 시나리오 평가")
    rank = df_view.sort_values("EDI", ascending=False).reset_index(drop=True)
    n = len(rank)
    top, mid = int(np.ceil(n*0.35)), int(np.floor(n*0.65))
    rank["grade"] = ["상위"]*n
    rank.loc[top:mid-1,"grade"]="중위"
    rank.loc[mid:,"grade"]="하위"

    st.dataframe(rank[["region","EDI","grade"]], use_container_width=True)

    st.markdown("### ✨ 해석")
    for _, r in rank.iterrows():
        if r.grade == "상위":
            st.markdown(f"- **{r.region}**: 🌟 경제활력 **우수** — 성장세 유지 가능")
        elif r.grade == "중위":
            st.markdown(f"- **{r.region}**: ➡️ **보통** — 정책·투자 따라 달라질 구간")
        else:
            st.markdown(f"- **{r.region}**: ⚠️ **취약** — 인구·구매력 저조, 개선 필요")

# ──────────────────────────────────────────
# 6. 원본 CSV 다운로드
# ──────────────────────────────────────────
st.sidebar.header("CSV 다운로드")
for lbl,upl in [("aligned_population.csv",pop_upl),
                ("aligned_households.csv",house_upl),
                ("aligned_ppi_fixed.csv",ppi_upl)]:
    st.sidebar.download_button(lbl+" 📥", upl.getvalue(), lbl)
