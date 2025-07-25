# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ──────────────────────────────────────────
# 0. 환경·용어 설명
# ──────────────────────────────────────────
st.set_page_config(page_title="시·도별 EDI 대시보드", layout="wide")
st.markdown("## 🚀 시·도별 경제발전지수(EDI) 대시보드 · 2021")

with st.expander("ℹ️ 용어"):
    st.markdown("""
- **PPI**: 잠재구매력지수 (Potential Purchasing Index)  
- **EDI**: `PPI × (총인구 ÷ 세대수)`로 산출한 간단 경제발전지수  
- **미래 전망**: PPI·가구당 인구수의 연평균 가정을 적용해 N 년 뒤 EDI 예측
""")

# ──────────────────────────────────────────
# 1. CSV 업로드
# ──────────────────────────────────────────
st.sidebar.header("정제 CSV 업로드")
pop_file   = st.sidebar.file_uploader("① aligned_population.csv",  type="csv")
house_file = st.sidebar.file_uploader("② aligned_households.csv", type="csv")
ppi_file   = st.sidebar.file_uploader("③ aligned_ppi_fixed.csv",  type="csv")

if not (pop_file and house_file and ppi_file):
    st.info("👈 3 CSV 모두 업로드하면 대시보드가 표시됩니다.")
    st.stop()

@st.cache_data(show_spinner=False)
def load_csv(upl): return pd.read_csv(upl, encoding="utf-8-sig")

pop_df   = load_csv(pop_file)
house_df = load_csv(house_file)
ppi_df   = load_csv(ppi_file)

# ──────────────────────────────────────────
# 2. 병합 · EDI 계산
# ──────────────────────────────────────────
df = (pop_df.merge(house_df, on="region", how="inner")
             .merge(ppi_df,   on="region", how="inner"))
if df.empty:
    st.error("`region` 이름이 맞지 않습니다.")
    st.stop()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ──────────────────────────────────────────
# 3. 시·도 필터 (17개 고정)
# ──────────────────────────────────────────
regions = df["region"].tolist()
sel = st.sidebar.multiselect("🔎 시·도 선택", regions, default=regions)
df_view = df[df["region"].isin(sel)] if sel else df

# ──────────────────────────────────────────
# 4. 뷰 선택
# ──────────────────────────────────────────
view = st.sidebar.radio(
    "보기",
    ["지표 막대", "EDI 순위", "인구·세대 막대", "미래 전망", "주관적 평가"]
)

# ---------- 4‑1. 지표 막대 ----------
if view == "지표 막대":
    st.subheader("📊 시·도별 주요 지표")
    long = df_view.melt(
        id_vars="region",
        value_vars=["total_population", "households", "PPI", "people_per_house", "EDI"],
        var_name="metric", value_name="value"
    )
    fig = px.bar(long, x="region", y="value", color="metric",
                 barmode="group", height=550,
                 labels={"value":"값","metric":"지표","region":"시·도"})
    st.plotly_chart(fig, use_container_width=True)

# ---------- 4‑2. EDI 순위 ----------
elif view == "EDI 순위":
    st.subheader("🏆 EDI 순위")
    fig = px.bar(df_view.sort_values("EDI", ascending=False),
                 x="EDI", y="region", orientation="h",
                 labels={"EDI":"EDI","region":"시·도"}, height=600)
    st.plotly_chart(fig, use_container_width=True)

# ---------- 4‑3. 인구·세대 ----------
elif view == "인구·세대 막대":
    st.subheader("👥 총인구 & 세대수")
    fig = px.bar(df_view.sort_values("total_population", ascending=False),
                 x="region", y=["total_population", "households"],
                 barmode="group",
                 labels={"value":"명 / 세대","variable":"지표","region":"시·도"},
                 height=550)
    st.plotly_chart(fig, use_container_width=True)

# ---------- 4‑4. 미래 전망 ----------
elif view == "미래 전망":
    st.subheader("🚀 미래 EDI 시뮬레이션")

    c1,c2,c3 = st.columns(3)
    yrs  = c1.number_input("N 년 뒤", 1, 30, 5)
    g_ppi= c2.slider("PPI 연 성장률(%)", -5.0, 10.0, 1.5, 0.1)
    g_pph= c3.slider("가구당 인구 연 변화율(%)", -3.0, 3.0, -0.5, 0.1)

    df_proj = df_view.copy()
    df_proj["EDI_future"] = (
        df_proj["EDI"]
        * (1 + g_ppi/100) ** yrs
        * (1 + g_pph/100) ** yrs
    )

    fig = px.bar(df_proj.sort_values("EDI_future", ascending=False),
                 x="EDI_future", y="region", orientation="h",
                 labels={"EDI_future":f"EDI (+{g_ppi}%·{g_pph}%/y, {yrs}y)", "region":"시·도"},
                 height=600)
    st.plotly_chart(fig, use_container_width=True)

# ---------- 4‑5. 주관적 평가 ----------
else:
    st.subheader("📝 주관적 지역 평가 (자동 분류)")

    # 3‑등급 분류 (상·중·하) : 상위 6 / 중간 6 / 하위 5
    df_rank = df_view.sort_values("EDI", ascending=False).reset_index(drop=True)
    n = len(df_rank)
    high_cut, low_cut = int(np.ceil(n*0.35)), int(np.floor(n*0.65))

    df_rank["grade"] = ["상위"]*n
    df_rank.loc[high_cut:low_cut-1, "grade"] = "중위"
    df_rank.loc[low_cut:, "grade"] = "하위"

    st.dataframe(df_rank[["region","EDI","grade"]], use_container_width=True)

    # 간략 해석
    def make_comment(row):
        if row["grade"]=="상위":
            return f"**{row.region}** → 현재 지표 우수, 성장 여건 양호"
        if row["grade"]=="중위":
            return f"**{row.region}** → 보통 수준, 정책·투자에 따라 변동성"
        return f"**{row.region}** → 개선 필요, 인구·PPI 모두 낮음"

    st.markdown("### ✨ 해석")
    for _, r in df_rank.iterrows():
        st.markdown("- " + make_comment(r))

# ──────────────────────────────────────────
# 5. 원본 파일 다시 다운로드
# ──────────────────────────────────────────
st.sidebar.header("정제 CSV 다운로드")
for lbl, upl in [("aligned_population.csv", pop_file),
                 ("aligned_households.csv", house_file),
                 ("aligned_ppi_fixed.csv", ppi_file)]:
    st.sidebar.download_button(lbl+" 📥", upl.getvalue(), lbl)
