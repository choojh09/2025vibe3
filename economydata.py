# app.py
import streamlit as st, pandas as pd, plotly.express as px, numpy as np, re

st.set_page_config(page_title="시·도 EDI 대시보드", layout="wide")
st.markdown("## 🚀 시·도별 경제발전지수(EDI) 대시보드 · 2021")

# ───────────────────────────────────────────
# 1) CSV 업로드
# ───────────────────────────────────────────
st.sidebar.header("정제 CSV 업로드")
pop_upl   = st.sidebar.file_uploader("① aligned_population.csv",  type="csv")
house_upl = st.sidebar.file_uploader("② aligned_households.csv", type="csv")
ppi_upl   = st.sidebar.file_uploader("③ aligned_ppi_fixed.csv",  type="csv")
if not (pop_upl and house_upl and ppi_upl):
    st.info("👈 세 CSV를 모두 업로드하세요.")
    st.stop()

@st.cache_data(show_spinner=False)
def read_csv(u): return pd.read_csv(u, encoding="utf-8-sig")

pop_raw, house_raw, ppi_raw = map(read_csv, [pop_upl, house_upl, ppi_upl])

def col_like(df, pats):
    return next((c for p in pats for c in df.columns if re.search(p, c, re.I)), None)

# 표준화
rc_pop, pc_pop = col_like(pop_raw,["region","지역","행정"]), col_like(pop_raw,["total","인구"])
rc_house, pc_house = col_like(house_raw,["region","지역","행정"]), col_like(house_raw,["house","세대"])
rc_ppi, pc_ppi = col_like(ppi_raw,["region","지역","행정"]), col_like(ppi_raw,["ppi","구매","index","지수"])

pop_df   = pop_raw[[rc_pop, pc_pop]].rename(columns={rc_pop:"region", pc_pop:"total_population"})
house_df = house_raw[[rc_house, pc_house]].rename(columns={rc_house:"region", pc_house:"households"})
ppi_df   = ppi_raw[[rc_ppi, pc_ppi]].rename(columns={rc_ppi:"region", pc_ppi:"PPI"})

for df in [pop_df, house_df, ppi_df]:
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

df = (pop_df.merge(house_df, on="region", how="inner")
             .merge(ppi_df,   on="region", how="inner")).dropna()

df["people_per_house"] = df["total_population"] / df["households"]
df["EDI"] = df["PPI"] * df["people_per_house"]

# ───────────────────────────────────────────
# 2) 필터
# ───────────────────────────────────────────
regions = df["region"].tolist()
sel_regions = st.sidebar.multiselect("시·도 선택", regions, default=regions)
df_view = df[df["region"].isin(sel_regions)] if sel_regions else df

# ───────────────────────────────────────────
# 3) 뷰
# ───────────────────────────────────────────
view = st.sidebar.radio(
    "보기",
    ["EDI 순위", "지표 막대", "인구·세대 막대", "미래 전망 + 평가"]
)

if view == "EDI 순위":
    st.subheader("🏆 EDI 순위")
    st.plotly_chart(
        px.bar(df_view.sort_values("EDI", ascending=False),
               x="EDI", y="region", orientation="h",
               labels={"EDI":"EDI","region":"시·도"}, height=600),
        use_container_width=True
    )

elif view == "지표 막대":
    st.subheader("📊 주요 지표")
    long = df_view.melt(id_vars="region",
                        value_vars=["total_population","households","PPI","people_per_house","EDI"],
                        var_name="metric", value_name="value")
    st.plotly_chart(
        px.bar(long, x="region", y="value", color="metric",
               barmode="group", height=550,
               labels={"value":"값","metric":"지표","region":"시·도"}),
        use_container_width=True
    )

elif view == "인구·세대 막대":
    st.subheader("👥 총인구 & 세대수")
    st.plotly_chart(
        px.bar(df_view.sort_values("total_population", ascending=False),
               x="region", y=["total_population","households"],
               barmode="group", height=550,
               labels={"value":"명 / 세대","variable":"지표","region":"시·도"}),
        use_container_width=True
    )

# ───────────────────────────────────────────
# 4) 미래 전망 + 주관적 평가
# ───────────────────────────────────────────
else:
    st.subheader("🚀 미래 EDI 전망 & 평가")

    col1,col2,col3 = st.columns(3)
    yrs  = col1.number_input("N 년 뒤", 1, 30, 5)
    g_ppi= col2.slider("PPI 연 성장률(%)", -5.0, 10.0, 1.5, 0.1)
    g_pph= col3.slider("가구당 인구 연 변화율(%)",-3.0, 3.0, -0.5, 0.1)

    df_future = df_view.copy()
    df_future["EDI_future"] = (
        df_future["EDI"] * (1+g_ppi/100)**yrs * (1+g_pph/100)**yrs
    )

    # 현재·미래 순위
    rank_now    = df_future["EDI"].rank(ascending=False, method="min")
    rank_future = df_future["EDI_future"].rank(ascending=False, method="min")
    df_future["rank_now"]    = rank_now
    df_future["rank_future"] = rank_future
    df_future["trend"] = np.where(rank_future < rank_now, "개선",
                          np.where(rank_future > rank_now, "악화", "유지"))

    # 등급(상·중·하) 기준: 미래 EDI 상위 35% / 중간 / 하위 35%
    n = len(df_future)
    top, mid = int(np.ceil(n*0.35)), int(np.floor(n*0.65))
    df_future = df_future.sort_values("EDI_future", ascending=False).reset_index(drop=True)
    df_future["grade"] = ["상위"]*n
    df_future.loc[top:mid-1,"grade"]="중위"
    df_future.loc[mid:,"grade"]="하위"

    # 그래프
    st.plotly_chart(
        px.bar(df_future,
               x="EDI_future", y="region", orientation="h",
               color="trend", color_discrete_map={"개선":"#2ca02c","유지":"#1f77b4","악화":"#d62728"},
               labels={"EDI_future":f"EDI(+{g_ppi}%·{g_pph}%/y, {yrs}y)","region":"시·도","trend":"전망"},
               height=600),
        use_container_width=True
    )

    # 표
    st.markdown("### 📋 상세 테이블")
    st.dataframe(df_future[["region","EDI","EDI_future","trend","grade"]],
                 use_container_width=True)

    # 해석
    st.markdown("### ✍️ 자동 해석")
    for _, r in df_future.iterrows():
        icon = {"개선":"⬆️","유지":"➡️","악화":"⬇️"}[r.trend]
        comment = {
            "상위":"경제 활력 **우수** 전망.",
            "중위":"정책·투자 따라 달라질 **보통**.",
            "하위":"**취약** — 개선 필요."
        }[r.grade]
        st.markdown(f"- {icon} **{r.region}**: {comment}")

# ───────────────────────────────────────────
# 5) CSV 다운로드
# ───────────────────────────────────────────
st.sidebar.header("CSV 다운로드")
for lbl,upl in [("aligned_population.csv",pop_upl),
                ("aligned_households.csv",house_upl),
                ("aligned_ppi_fixed.csv",ppi_upl)]:
    st.sidebar.download_button(lbl+" 📥", upl.getvalue(), lbl)
