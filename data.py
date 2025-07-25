import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
import re

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
st.set_page_config(page_title="인구 대시보드", layout="wide")

# 자동 다운로드용 URL (실제 URL이 없으면 실패합니다)
MF_URL    = "https://example.com/202506_연령별인구현황_월간_남여구분.csv"
TOTAL_URL = "https://example.com/202506_연령별인구현황_월간_합계.csv"

# 로컬에 미리 저장해둔 파일 경로
LOCAL_MF_PATH    = "data/202506_202506_연령별인구현황_월간 남여구분.csv"
LOCAL_TOTAL_PATH = "data/202506_202506_연령별인구현황_월간 합계.csv"

@st.cache_data
def load_csv_from_url(url: str) -> pd.DataFrame | None:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return pd.read_csv(io.BytesIO(r.content), encoding="cp949")
    except Exception:
        return None


def load_csv_from_local(path: str) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, encoding="cp949")
    except Exception:
        return None

# ───────────────────────────────────────────
# 데이터 로드: URL → 로컬 → 업로드
# ───────────────────────────────────────────
df_mf    = load_csv_from_url(MF_URL)
df_total = load_csv_from_url(TOTAL_URL)

# URL 실패 시 로컬 파일 시도
if df_mf is None:
    df_mf = load_csv_from_local(LOCAL_MF_PATH)
    if df_mf is not None:
        st.sidebar.success("✅ 로컬에서 남여구분 CSV를 불러왔습니다.")
if df_total is None:
    df_total = load_csv_from_local(LOCAL_TOTAL_PATH)
    if df_total is not None:
        st.sidebar.success("✅ 로컬에서 합계 CSV를 불러왔습니다.")

# 그래도 없으면 업로드 위젯
if df_mf is None or df_total is None:
    st.sidebar.warning("⚠️ 자동 로드에 실패했습니다. 직접 CSV를 업로드하세요.")
    uploaded_mf    = st.sidebar.file_uploader("남여구분 CSV 업로드",    type="csv")
    uploaded_tot   = st.sidebar.file_uploader("합계 CSV 업로드",      type="csv")
    if uploaded_mf:
        df_mf    = pd.read_csv(io.BytesIO(uploaded_mf.read()), encoding="cp949")
    if uploaded_tot:
        df_total = pd.read_csv(io.BytesIO(uploaded_tot.read()), encoding="cp949")

# ───────────────────────────────────────────
# 본격 시각화
# ───────────────────────────────────────────
if df_mf is not None and df_total is not None:
    # 행정구역 컬럼 자동 감지
    region_col = next((c for c in df_mf.columns if any(k in c for k in ["행정","지역","시군구"])),
                      df_mf.columns[0])
    regions = df_mf[region_col].unique().tolist()
    sel_region = st.sidebar.selectbox("📍 시·군·구 선택", regions)

    # 선택 행
    row_mf  = df_mf[df_mf[region_col] == sel_region].iloc[0]
    row_tot = df_total[df_total[region_col] == sel_region].iloc[0]

    # 연령·성별 파싱
    male_cols = [c for c in df_mf.columns if "_남_" in c and "세" in c]
    ages      = [c.split("_")[-1] for c in male_cols]
    to_int    = lambda x: int(str(x).replace(",",""))

    male_counts   = [to_int(row_mf[c]) for c in male_cols]
    female_counts = [to_int(row_mf[c.replace("_남_","_여_")]) for c in male_cols]
    total_cols    = [c for c in df_total.columns if "_계_" in c and "세" in c]
    total_counts  = [to_int(row_tot[c]) for c in total_cols]

    # 페이지 선택
    page = st.sidebar.radio("🔎 페이지 선택", ["지역별", "성별별", "연령대별"])

    if page == "지역별":
        st.header(f"📊 {sel_region} 인구 현황 (2025‑06)")
        # 피라미드
        df_p = pd.DataFrame({"연령": ages, "남자": male_counts, "여자": female_counts})
        fig1 = px.bar(df_p, y="연령", x="남자", orientation="h", text="남자",
                      labels={"남자":"인구수","연령":""})
        fig2 = px.bar(df_p, y="연령", x="여자", orientation="h", text="여자",
                      labels={"여자":"인구수","연령":""})
        # 총인구
        df_t = pd.DataFrame({"연령": ages, "총인구": total_counts})
        fig3 = px.bar(df_t, x="연령", y="총인구",
                      labels={"총인구":"인구수","연령":""})

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(fig1.update_layout(yaxis=dict(autorange="reversed")), use_container_width=True)
            st.plotly_chart(fig2.update_layout(yaxis=dict(autorange="reversed")), use_container_width=True)
        with c2:
            st.plotly_chart(fig3, use_container_width=True)

    elif page == "성별별":
        st.header(f"📈 {sel_region} 성별 인구 분포 (2025‑06)")
        gender = st.sidebar.selectbox("👥 성별 선택", ["남자","여자"])
        counts = male_counts if gender=="남자" else female_counts
        df_g = pd.DataFrame({"연령": ages, "인구수": counts})
        fig = px.bar(df_g, x="연령", y="인구수",
                     labels={"연령":"","인구수":"인구수"})
        st.plotly_chart(fig, use_container_width=True)

    else:  # 연령대별
        st.header(f"📊 {sel_region} 10세 단위 연령대별 인구 비교 (2025‑06)")
        # 나이 숫자 변환
        nums = []
        for a in ages:
            m = re.search(r"(\d+)", a)
            nums.append(int(m.group(1)) if m else 0)
        # 연령대 지정
        bins = list(range(0, 101, 10)) + [200]
        labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]

        df_age = pd.DataFrame({
            "age": nums,
            "남자": male_counts,
            "여자": female_counts
        })
        df_age["연령대"] = pd.cut(df_age["age"], bins=bins, labels=labels, right=False)
        df_grp = df_age.groupby("연령대")[['남자','여자']].sum().reset_index()

        fig = px.bar(
            df_grp,
            x="연령대",
            y=["남자","여자"],
            barmode="group",
            labels={"value":"인구수","variable":"성별","연령대":"연령대"}
        )
        st.plotly_chart(fig, use_container_width=True)

    # 원본 데이터 보기
    with st.expander("📑 원본 데이터 보기"):
        st.write("남여구분 데이터:")
        st.dataframe(row_mf.to_frame().T, use_container_width=True)
        st.write("합계 데이터:")
        st.dataframe(row_tot.to_frame().T, use_container_width=True)

else:
    st.info("데이터를 불러오는 중입니다…")
