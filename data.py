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

# 로컬 CSV 파일 경로
LOCAL_MF_PATH    = "data/202506_202506_연령별인구현황_월간 남여구분.csv"
LOCAL_TOTAL_PATH = "data/202506_202506_연령별인구현황_월간 합계.csv"

# ───────────────────────────────────────────
# 데이터 로드 함수
# ───────────────────────────────────────────
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
# 데이터 불러오기: URL → 로컬 → 업로드
# ───────────────────────────────────────────

df_mf    = load_csv_from_url(MF_URL)
df_total = load_csv_from_url(TOTAL_URL)

if df_mf is None:
    df_mf = load_csv_from_local(LOCAL_MF_PATH)
    if df_mf is not None:
        st.sidebar.success("✅ 로컬에서 남여구분 CSV 로드 성공")
if df_total is None:
    df_total = load_csv_from_local(LOCAL_TOTAL_PATH)
    if df_total is not None:
        st.sidebar.success("✅ 로컬에서 합계 CSV 로드 성공")

if df_mf is None or df_total is None:
    st.sidebar.warning("⚠️ 데이터 로드 실패: CSV를 업로드해주세요.")
    uploaded_mf  = st.sidebar.file_uploader("남여구분 CSV 업로드", type="csv")
    uploaded_tot = st.sidebar.file_uploader("합계 CSV 업로드", type="csv")
    if uploaded_mf:
        df_mf = pd.read_csv(io.BytesIO(uploaded_mf.read()), encoding="cp949")
    if uploaded_tot:
        df_total = pd.read_csv(io.BytesIO(uploaded_tot.read()), encoding="cp949")

# ───────────────────────────────────────────
# 본격 시각화
# ───────────────────────────────────────────

if df_mf is not None and df_total is not None:
    # 행정구역 컬럼 자동 감지
    region_col = next((c for c in df_mf.columns if any(k in c for k in ["행정","지역","시군구"])), df_mf.columns[0])

    # 연령·성별 컬럼 목록
    male_cols = [c for c in df_mf.columns if "_남_" in c and "세" in c]
    age_labels = [c.split("_")[-1] for c in male_cols]
    to_int = lambda x: int(str(x).replace(",",""))

    # 합계용 컬럼
    total_cols = [c for c in df_total.columns if "_계_" in c and "세" in c]

    # 행정구역에서 상위 지역(특별시/광역시/도) 추출
    def get_province(name: str) -> str:
        m = re.match(r"(.+?(?:특별시|광역시|도))", name)
        return m.group(1) if m else name

    df_total['province'] = df_total[region_col].apply(get_province)

    # 사이드바: 페이지 선택
    page = st.sidebar.radio("🔎 페이지 선택", ["지역별", "성별별", "연령대별"])

    if page == "지역별":
        st.header("📈 지역별(도/광역시) 연령 분포 꺾은선 그래프")
        # 상위 지역 리스트
        provinces = sorted(df_total['province'].unique().tolist())        default_provinces = [p for p in ["서울특별시", "전라북도"] if p in provinces]
        sel_provinces = st.sidebar.multiselect("📍 지역 그룹 선택", provinces, default=default_provinces)
        if not sel_provinces:
            sel_provinces = provinces

        # 각 상위 지역별 연령대별 총인구 합계 계산
        data = {'연령': age_labels}
        for prov in sel_provinces:
            df_sub = df_total[df_total['province'] == prov]
            # 각 연령별 합계
            counts = [df_sub[col].apply(to_int).sum() for col in total_cols]
            data[prov] = counts
        df_line = pd.DataFrame(data)

        # 꺾은선 그래프
        fig = px.line(df_line, x='연령', y=sel_provinces, markers=True,
                      labels={'value':'인구수','연령':''})
        st.plotly_chart(fig, use_container_width=True)

    elif page == "성별별":
        # 기존 성별별 연령별 막대 그래프 유지
        st.header("📊 성별별 연령 분포")
        sel_region = st.sidebar.selectbox("📍 시·군·구 선택", df_mf[region_col].unique().tolist())
        row_mf = df_mf[df_mf[region_col] == sel_region].iloc[0]
        male_counts   = [to_int(row_mf[c]) for c in male_cols]
        female_counts = [to_int(row_mf[c.replace('_남_','_여_')]) for c in male_cols]
        gender = st.sidebar.selectbox("👥 성별 선택", ['남자','여자'], index=0)
        counts = male_counts if gender=='남자' else female_counts
        df_gen = pd.DataFrame({'연령': age_labels, '인구수': counts})
        fig = px.bar(df_gen, x='연령', y='인구수', labels={'인구수':'인구수','연령':''})
        st.plotly_chart(fig, use_container_width=True)

    else:  # 연령대별
        st.header("📊 연령대별 인구 비교 꺾은선 그래프")
        # 나이 수치
        ages_num = [int(re.search(r"(\d+)", a).group(1)) for a in age_labels]
        bins = list(range(0, 101, 10)) + [200]
        labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
        # 데이터프레임
        df_age = pd.DataFrame({'age': ages_num})
        df_age['province'] = df_total[region_col].apply(get_province)
        df_age['total'] = 0  # placeholder
        # 원본 총인구값 매핑
        for col, age in zip(total_cols, ages_num):
            df_age.loc[df_age['age'] == age, 'total'] = df_total[col].apply(to_int).tolist()[0]
        # 그룹화
        df_age['연령대'] = pd.cut(df_age['age'], bins=bins, labels=labels, right=False)
        df_grp = df_age.groupby('연령대')['total'].sum().reset_index()
        fig = px.line(df_grp, x='연령대', y='total', markers=True,
                      labels={'total':'인구수','연령대':'연령대'})
        st.plotly_chart(fig, use_container_width=True)

    # 원본 데이터 보기
    with st.expander("📑 원본 데이터 보기"):
        st.write("남여구분 데이터:")
        st.dataframe(df_mf.head(), use_container_width=True)
        st.write("합계 데이터:")
        st.dataframe(df_total.head(), use_container_width=True)

else:
    st.info("데이터를 불러오는 중입니다…")
