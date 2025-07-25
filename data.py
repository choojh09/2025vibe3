import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# ────────────────────────────────────────────────────
# 1) 설정
# ────────────────────────────────────────────────────
st.set_page_config(page_title="인구 대시보드", layout="wide")

# 자동 다운로드할 CSV URL (실제 공개 URL로 바꿔주세요)
MF_URL    = "https://example.com/202506_연령별인구현황_월간_남여구분.csv"
TOTAL_URL = "https://example.com/202506_연령별인구현황_월간_합계.csv"

@st.cache_data
def load_csv_from_url(url: str) -> pd.DataFrame:
    r = requests.get(url)
    r.raise_for_status()
    return pd.read_csv(io.BytesIO(r.content), encoding="cp949")

# 데이터 로드
df_mf    = load_csv_from_url(MF_URL)
df_total = load_csv_from_url(TOTAL_URL)

# 행정구역(시·군·구) 컬럼 찾기
region_col = next(
    (c for c in df_mf.columns if any(k in c for k in ["행정", "지역", "시군구"])),
    df_mf.columns[0]
)

# ────────────────────────────────────────────────────
# 2) 사이드바: 페이지 선택, 공통 필터
# ────────────────────────────────────────────────────
page = st.sidebar.radio("🔎 페이지 선택", ["지역별", "성별별", "연령대별"])
regions = df_mf[region_col].unique().tolist()
sel_region = st.sidebar.selectbox("📍 시·군·구 선택", regions)

# 선택된 행
row_mf    = df_mf[df_mf[region_col] == sel_region].iloc[0]
row_total = df_total[df_total[region_col] == sel_region].iloc[0]

# 나이 컬럼과 레이블 파싱
male_cols = [c for c in df_mf.columns if "_남_" in c and "세" in c]
age_labels = [c.split("_")[-1] for c in male_cols]

def to_int(x): return int(str(x).replace(",", ""))

male_counts   = [to_int(row_mf[c]) for c in male_cols]
female_counts = [to_int(row_mf[c.replace("_남_", "_여_")]) for c in male_cols]
total_cols    = [c for c in df_total.columns if "_계_" in c and "세" in c]
total_counts  = [to_int(row_total[c]) for c in total_cols]

# ────────────────────────────────────────────────────
# 3) 페이지별 뷰
# ────────────────────────────────────────────────────
if page == "지역별":
    st.header(f"📊 {sel_region} 인구 현황 (2025‑06)")
    # 인구 피라미드
    df_pyr = pd.DataFrame({
        "연령": age_labels,
        "남자": male_counts,
        "여자": female_counts
    })
    fig_pyr = px.bar(
        df_pyr,
        y="연령",
        x="남자",
        orientation="h",
        text="남자",
        title="인구 피라미드 (남자)",
        labels={"남자":"인구수","연령":""}
    )
    fig_pyr2 = px.bar(
        df_pyr,
        y="연령",
        x="여자",
        orientation="h",
        text="여자",
        title="인구 피라미드 (여자)",
        labels={"여자":"인구수","연령":""}
    )
    # 총인구 막대
    df_tot = pd.DataFrame({
        "연령": age_labels,
        "총인구": total_counts
    })
    fig_tot = px.bar(
        df_tot,
        x="연령",
        y="총인구",
        title="연령별 총인구수",
        labels={"총인구":"인구수","연령":""}
    )

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(fig_pyr.update_layout(yaxis=dict(autorange="reversed")), use_container_width=True)
        st.plotly_chart(fig_pyr2.update_layout(yaxis=dict(autorange="reversed")), use_container_width=True)
    with c2:
        st.plotly_chart(fig_tot, use_container_width=True)

elif page == "성별별":
    st.header(f"📈 {sel_region} 성별 인구 분포 (2025‑06)")
    gender = st.sidebar.selectbox("👥 성별 선택", ["남자", "여자"])
    counts = male_counts if gender == "남자" else female_counts
    df_gen = pd.DataFrame({"연령": age_labels, "인구수": counts})
    fig = px.bar(
        df_gen,
        x="연령",
        y="인구수",
        title=f"{gender} 연령별 인구수",
        labels={"연령":"","인구수":"인구수"}
    )
    st.plotly_chart(fig, use_container_width=True)

else:  # 연령대별
    st.header(f"📊 {sel_region} 연령대별 인구 합계 (2025‑06)")
    # 10세 단위 그룹화
    ages_num = [int(a.replace("세","")) for a in age_labels]
    df_age = pd.DataFrame({"age": ages_num, "count": total_counts})
    bins = list(range(0, 101, 10)) + [200]
    labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    df_age["연령대"] = pd.cut(df_age["age"], bins=bins, labels=labels, right=False)
    df_grp = df_age.groupby("연령대")["count"].sum().reset_index()
    fig = px.bar(
        df_grp,
        x="연령대",
        y="count",
        title="10세 단위 연령대별 인구수",
        labels={"연령대":"연령대","count":"인구수"}
    )
    st.plotly_chart(fig, use_container_width=True)
