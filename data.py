import streamlit as st
import pandas as pd
import plotly.express as px
import re
import io

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
st.set_page_config(page_title="인구 대시보드", layout="wide")
st.title("📊 인구 대시보드 (지역별/성별별/연령대별)")

# ───────────────────────────────────────────
# 파일 업로드
# ───────────────────────────────────────────
st.sidebar.header("CSV 파일 업로드")
mf_file = st.sidebar.file_uploader(
    "남여구분 CSV (예: 202506_연령별인구현황_월간 남여구분.csv)",
    type="csv"
)
total_file = st.sidebar.file_uploader(
    "합계 CSV (예: 202506_연령별인구현황_월간 합계.csv)",
    type="csv"
)

# ───────────────────────────────────────────
# 파일 로드
# ───────────────────────────────────────────
if mf_file is not None and total_file is not None:
    try:
        df_mf = pd.read_csv(io.BytesIO(mf_file.read()), encoding="cp949")
        df_total = pd.read_csv(io.BytesIO(total_file.read()), encoding="cp949")
    except Exception as e:
        st.error(f"CSV 파일 읽기 오류: {e}")
        st.stop()
else:
    st.info("왼쪽 사이드바에서 두 개의 CSV 파일을 업로드 해주세요.")
    st.stop()

# ───────────────────────────────────────────
# 컬럼 및 함수 정의
# ───────────────────────────────────────────
region_col = next(
    (c for c in df_mf.columns if any(k in c for k in ["행정","지역","시군구"])),
    df_mf.columns[0]
)
male_cols  = [c for c in df_mf.columns if "_남_" in c and "세" in c]
age_labels = [c.split("_")[-1] for c in male_cols]
to_int     = lambda x: int(str(x).replace(",",""))
total_cols = [c for c in df_total.columns if "_계_" in c and "세" in c]

# 상위 지역 추출 함수
def get_province(name: str) -> str:
    m = re.match(r"(.+?(?:특별시|광역시|도))", name)
    return m.group(1) if m else name

# province 컬럼 추가
df_total["province"] = df_total[region_col].apply(get_province)
df_mf["province"]    = df_mf[region_col].apply(get_province)

# ───────────────────────────────────────────
# 사이드바: 페이지 선택
# ───────────────────────────────────────────
page = st.sidebar.radio("페이지 선택", ["지역별", "성별별", "연령대별"])

# ───────────────────────────────────────────
# 페이지별 뷰
# ───────────────────────────────────────────
if page == "지역별":
    st.header("📈 지역별(시·도) 연령별 총인구 꺾은선 그래프")
    provinces = sorted(df_total["province"].unique())
    sel_provinces = st.sidebar.multiselect("지역 선택", provinces, default=provinces)
    if not sel_provinces:
        sel_provinces = provinces

    data = {"연령": age_labels}
    for prov in sel_provinces:
        df_sub = df_total[df_total["province"] == prov]
        counts = [df_sub[col].apply(to_int).sum() for col in total_cols]
        data[prov] = counts
    df_line = pd.DataFrame(data)

    fig = px.line(df_line, x="연령", y=sel_provinces, markers=True,
                  labels={"value":"인구수","연령":""})
    st.plotly_chart(fig, use_container_width=True)

elif page == "성별별":
    st.header("📊 시·군·구별 성별 연령 분포")
    regions = df_mf[region_col].unique().tolist()
    sel_region = st.sidebar.selectbox("시·군·구 선택", regions)
    row = df_mf[df_mf[region_col] == sel_region].iloc[0]

    male_counts   = [to_int(row[c]) for c in male_cols]
    female_counts = [to_int(row[c.replace("_남_","_여_")]) for c in male_cols]

    df_gen = pd.DataFrame({
        "연령": age_labels,
        "남자": male_counts,
        "여자": female_counts
    })
    fig = px.bar(df_gen, x="연령", y=["남자","여자"], barmode="group",
                 labels={"value":"인구수","variable":"성별","연령":""})
    st.plotly_chart(fig, use_container_width=True)

else:  # 연령대별
    st.header("📊 10세 단위 연령대별 인구 꺾은선 그래프")
    ages_num = [int(re.search(r"(\d+)", a).group(1)) for a in age_labels]
    total_counts = [df_total[col].apply(to_int).sum() for col in total_cols]

    df_age = pd.DataFrame({
        "age": ages_num,
        "total": total_counts
    })
    bins = list(range(0, 101, 10)) + [200]
    labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    df_age["연령대"] = pd.cut(df_age["age"], bins=bins, labels=labels, right=False)

    df_grp = df_age.groupby("연령대")["total"].sum().reset_index()
    fig = px.line(df_grp, x="연령대", y="total", markers=True,
                  labels={"total":"인구수","연령대":"연령대"})
    st.plotly_chart(fig, use_container_width=True)
