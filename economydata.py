# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io, re

# ─────────────────────────────
# 0. 페이지 기본 설정
# ─────────────────────────────
st.set_page_config(page_title="한국 지역별 경제지표 대시보드", layout="wide")
st.title("📈 한국 지역별 경제발전지수(EDI) 대시보드 · 2021")

# ─────────────────────────────
# 1. CSV 업로드
# ─────────────────────────────
st.sidebar.header("CSV 2종 업로드")
pop_file = st.sidebar.file_uploader("① 2021 연령별 인구현황 (정제 CSV)", type="csv")
ppi_file = st.sidebar.file_uploader("② 잠재구매력지수 (정제 CSV)", type="csv")

if not (pop_file and ppi_file):
    st.info("👈 왼쪽에서 두 CSV를 모두 업로드하세요.")
    st.stop()

# ─────────────────────────────
# 2. 범용 CSV 로더
# ─────────────────────────────
def robust_read(uploaded_file):
    raw = uploaded_file.read()
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    seps = [",", ";", "|", "\t"]
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=sep)
                if not df.empty and len(df.columns) > 1:
                    return df
            except Exception:
                continue
    return pd.read_csv(io.BytesIO(raw), engine="python")

pop_df = robust_read(pop_file)
ppi_df = robust_read(ppi_file)

# ─────────────────────────────
# 3. 지역명 표준화 함수
# ─────────────────────────────
CANON = {
    "서울": "서울특별시", "서울특별시": "서울특별시", "서울시": "서울특별시",
    "부산": "부산광역시", "부산광역시": "부산광역시",
    "대구": "대구광역시", "대구광역시": "대구광역시",
    "인천": "인천광역시", "인천광역시": "인천광역시",
    "광주": "광주광역시", "광주광역시": "광주광역시",
    "대전": "대전광역시", "대전광역시": "대전광역시",
    "울산": "울산광역시", "울산광역시": "울산광역시",
    "세종": "세종특별자치시", "세종특별자치시": "세종특별자치시",
    "경기": "경기도", "경기도": "경기도",
    "강원": "강원도", "강원도": "강원도",
    "충북": "충청북도", "충청북도": "충청북도",
    "충남": "충청남도", "충청남도": "충청남도",
    "전북": "전라북도", "전라북도": "전라북도",
    "전남": "전라남도", "전라남도": "전라남도",
    "경북": "경상북도", "경상북도": "경상북도",
    "경남": "경상남도", "경상남도": "경상남도",
    "제주": "제주특별자치도", "제주특별자치도": "제주특별자치도",
}

def normalize_region(name: str) -> str:
    name = name.strip()
    for k, v in CANON.items():
        if name == k or name == v:
            return v
        if name.startswith(k + " "):
            return v + name[len(k):]
        if name.startswith(v + " "):
            return v + name[len(v):]
    return name  # 그대로

def detect_region_col(df):
    for c in df.columns:
        if any(key in c for key in ["행정", "지역", "시군구"]):
            return c
    return df.columns[0]

# 표준화 적용
reg_pop_col = detect_region_col(pop_df)
reg_ppi_col = detect_region_col(ppi_df)

pop_df[reg_pop_col] = pop_df[reg_pop_col].astype(str).apply(normalize_region)
ppi_df[reg_ppi_col] = ppi_df[reg_ppi_col].astype(str).apply(normalize_region)

# ─────────────────────────────
# 4. 인구 데이터 가공
# ─────────────────────────────
male_cols = [c for c in pop_df.columns if "_남_" in c and c.endswith("세")]
female_cols = [c.replace("_남_", "_여_") for c in male_cols]
all_age_cols = male_cols + female_cols
pop_df[all_age_cols] = pop_df[all_age_cols].apply(
    lambda s: s.astype(str).str.replace(",", "").astype(int)
)

# 가동연령(15~64) 컬럼
work_cols = [
    c for c in all_age_cols
    if 15 <= int(re.search(r"(\\d{1,3})세", c).group(1)) <= 64
]

pop_df["total_pop"] = pop_df[all_age_cols].sum(axis=1)
pop_df["work_pop"] = pop_df[work_cols].sum(axis=1)
pop_df["work_ratio"] = pop_df["work_pop"] / pop_df["total_pop"] * 100  # %

# ─────────────────────────────
# 5. PPI 데이터 가공
# ─────────────────────────────
ppi_value_col = next(
    (c for c in ppi_df.columns if re.search(r"ppi|구매", c, re.I)),
    ppi_df.columns[1],
)
ppi_df = (
    ppi_df[[reg_ppi_col, ppi_value_col]]
    .rename(columns={reg_ppi_col: "region", ppi_value_col: "PPI"})
)
ppi_df["PPI"] = pd.to_numeric(ppi_df["PPI"], errors="coerce")
ppi_df = ppi_df.groupby("region", as_index=False)["PPI"].mean()

# ─────────────────────────────
# 6. 지표 계산 (EDI)
# ─────────────────────────────
merged = (
    pop_df[[reg_pop_col, "total_pop", "work_ratio"]]
    .rename(columns={reg_pop_col: "region"})
    .merge(ppi_df, on="region", how="left")
)
missing = merged["PPI"].isna().sum()
if missing:
    st.sidebar.warning(f"⚠️ PPI 데이터가 없는 지역 {missing}곳은 EDI 계산 제외")

merged = merged.dropna(subset=["PPI"])
merged["EDI"] = merged["PPI"] * (merged["work_ratio"] / 100)

if merged.empty:
    st.error("❌ 공통 지역이 하나도 없습니다. 파일의 지역명을 확인하세요.")
    st.stop()

# ─────────────────────────────
# 7. 대시보드 뷰
# ─────────────────────────────
view = st.sidebar.radio("보기 선택", ["지역별 표", "EDI 산점도", "인구 피라미드"])

if view == "지역별 표":
    st.subheader("📋 지역별 경제발전지수(EDI) 표")
    st.dataframe(
        merged.sort_values("EDI", ascending=False).reset_index(drop=True),
        use_container_width=True,
    )

elif view == "EDI 산점도":
    st.subheader("🔍 경제발전지수(EDI) vs 가동연령비")
    fig = px.scatter(
        merged,
        x="work_ratio",
        y="EDI",
        size="total_pop",
        text="region",
        labels={
            "work_ratio": "가동연령비 (%)",
            "EDI": "경제발전지수(EDI)",
            "total_pop": "인구수",
        },
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

else:  # 인구 피라미드
    region_list = merged["region"].tolist()
    sel_region = st.sidebar.selectbox("피라미드 지역 선택", region_list)

    row = pop_df[pop_df[reg_pop_col] == sel_region].iloc[0]
    male_vals = [-row[c] for c in male_cols]
    female_vals = [row[c] for c in female_cols]
    ages = [c.split("_")[-1] for c in male_cols]

    fig = go.Figure()
    fig.add_bar(y=ages, x=male_vals, name="남자", orientation="h")
    fig.add_bar(y=ages, x=female_vals, name="여자", orientation="h")
    fig.update_layout(
        title=f"{sel_region} 인구 피라미드 (2021)",
        barmode="overlay",
        bargap=0.05,
        height=700,
        xaxis_title="인구수",
        yaxis_title="연령",
    )
    st.plotly_chart(fig, use_container_width=True)
