import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from requests.exceptions import HTTPError

st.set_page_config(page_title="인구 대시보드", layout="wide")

# ────────────────────────────────────────────────────
# 0) 데이터 로드 함수들
# ────────────────────────────────────────────────────
@st.cache_data
def load_csv_from_url(url: str) -> pd.DataFrame | None:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return pd.read_csv(io.BytesIO(r.content), encoding="cp949")
    except HTTPError as e:
        st.error(f"🔴 URL에서 데이터를 가져오지 못했습니다:\n{e}")
        return None
    except Exception as e:
        st.error(f"🔴 데이터 로드 중 오류 발생:\n{e}")
        return None

def load_csv_from_upload(uploaded_file) -> pd.DataFrame | None:
    if not uploaded_file:
        return None
    try:
        return pd.read_csv(io.BytesIO(uploaded_file.read()), encoding="cp949")
    except Exception as e:
        st.error(f"🔴 업로드된 CSV 읽기 실패:\n{e}")
        return None

# ────────────────────────────────────────────────────
# 1) 자동 다운로드 시도
# ────────────────────────────────────────────────────
MF_URL    = "https://example.com/202506_연령별인구현황_월간_남여구분.csv"
TOTAL_URL = "https://example.com/202506_연령별인구현황_월간_합계.csv"

df_mf    = load_csv_from_url(MF_URL)
df_total = load_csv_from_url(TOTAL_URL)

# ────────────────────────────────────────────────────
# 2) 다운로드 실패 시 업로드 폼 보여주기
# ────────────────────────────────────────────────────
if df_mf is None or df_total is None:
    st.sidebar.warning("⚠️ 자동 다운로드에 실패했습니다. CSV 파일을 직접 업로드하세요.")
    uploaded_mf    = st.sidebar.file_uploader("남여구분 CSV 업로드", type="csv")
    uploaded_total = st.sidebar.file_uploader("합계 CSV 업로드", type="csv")

    if uploaded_mf:    df_mf    = load_csv_from_upload(uploaded_mf)
    if uploaded_total: df_total = load_csv_from_upload(uploaded_total)

# ────────────────────────────────────────────────────
# 3) 데이터 준비 & 시각화
# ────────────────────────────────────────────────────
if df_mf is not None and df_total is not None:
    # 행정구역 컬럼 자동 감지
    region_col = next(
        (c for c in df_mf.columns if any(k in c for k in ["행정", "지역", "시군구"])),
        df_mf.columns[0]
    )
    regions = df_mf[region_col].unique().tolist()
    sel_region = st.sidebar.selectbox("📍 시·군·구 선택", regions)

    # 선택된 행
    row_mf    = df_mf[df_mf[region_col] == sel_region].iloc[0]
    row_total = df_total[df_total[region_col] == sel_region].iloc[0]

    # 연령·성별 데이터 파싱
    male_cols = [c for c in df_mf.columns if "_남_" in c and "세" in c]
    age_labels = [c.split("_")[-1] for c in male_cols]
    to_int = lambda x: int(str(x).replace(",", ""))

    male_counts   = [to_int(row_mf[c]) for c in male_cols]
    female_counts = [to_int(row_mf[c.replace("_남_", "_여_")]) for c in male_cols]
    total_cols    = [c for c in df_total.columns if "_계_" in c and "세" in c]
    total_counts  = [to_int(row_total[c]) for c in total_cols]

    page = st.sidebar.radio("🔎 페이지 선택", ["지역별", "성별별", "연령대별"])

    if page == "지역별":
        st.header(f"📊 {sel_region} 인구 현황 (2025‑06)")
        df_pyr = pd.DataFrame({"연령": age_labels, "남자": male_counts, "여자": female_counts})
        fig_pyr = px.bar(df_pyr, y="연령", x="남자", orientation="h", text="남자",
                         labels={"남자":"인구수","연령":""})
        fig_pyr2= px.bar(df_pyr, y="연령", x="여자", orientation="h", text="여자",
                         labels={"여자":"인구수","연령":""})
        df_tot = pd.DataFrame({"연령": age_labels, "총인구": total_counts})
        fig_tot= px.bar(df_tot, x="연령", y="총인구", labels={"총인구":"인구수","연령":""})

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fig_pyr.update_layout(yaxis=dict(autorange="reversed")), use_container_width=True)
            st.plotly_chart(fig_pyr2.update_layout(yaxis=dict(autorange="reversed")), use_container_width=True)
        with c2:
            st.plotly_chart(fig_tot, use_container_width=True)

    elif page == "성별별":
        st.header(f"📈 {sel_region} 성별 인구 분포 (2025‑06)")
        gender = st.sidebar.selectbox("👥 성별 선택", ["남자", "여자"])
        counts = male_counts if gender=="남자" else female_counts
        df_gen = pd.DataFrame({"연령": age_labels, "인구수": counts})
        fig = px.bar(df_gen, x="연령", y="인구수",
                     labels={"연령":"","인구수":"인구수"})
        st.plotly_chart(fig, use_container_width=True)

    else:  # 연령대별
        st.header(f"📊 {sel_region} 연령대별 인구 합계 (2025‑06)")
        ages_num = [int(a.replace("세","")) for a in age_labels]
        df_age = pd.DataFrame({"age": ages_num, "count": total_counts})
        bins = list(range(0, 101, 10)) + [200]
        labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
        df_age["연령대"] = pd.cut(df_age["age"], bins=bins, labels=labels, right=False)
        df_grp = df_age.groupby("연령대")["count"].sum().reset_index()
        fig = px.bar(df_grp, x="연령대", y="count",
                     labels={"연령대":"연령대","count":"인구수"})
        st.plotly_chart(fig, use_container_width=True)

    # 원본 데이터 보기
    with st.expander("📑 원본 데이터 보기"):
        st.write("남여구분 데이터:")
        st.dataframe(row_mf.to_frame().T, use_container_width=True)
        st.write("합계 데이터:")
        st.dataframe(row_total.to_frame().T, use_container_width=True)

else:
    st.info("데이터 로드 중입니다...")
