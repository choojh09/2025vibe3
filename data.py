import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import io

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
st.set_page_config(page_title="인구 피라미드 대시보드", layout="wide")
st.title("📊 인구 피라미드 대시보드 (시/도 → 시·군·구 선택)")

# ───────────────────────────────────────────
# CSV 파일 업로드
# ───────────────────────────────────────────
st.sidebar.header("CSV 파일 업로드")
mf_file = st.sidebar.file_uploader("남여구분 CSV (예: …남여구분.csv)", type="csv")
total_file = st.sidebar.file_uploader("합계 CSV (예: …합계.csv)", type="csv")
if not mf_file or not total_file:
    st.info("왼쪽에서 두 개의 CSV 파일을 업로드해주세요.")
    st.stop()
try:
    df_mf = pd.read_csv(io.BytesIO(mf_file.read()), encoding="cp949")
    df_total = pd.read_csv(io.BytesIO(total_file.read()), encoding="cp949")
except Exception as e:
    st.error(f"CSV 파일 읽기 오류: {e}")
    st.stop()

# ───────────────────────────────────────────
# 컬럼 및 유틸 함수 정의
# ───────────────────────────────────────────
region_col = next((c for c in df_mf.columns if any(k in c for k in ["행정","지역","시군구"])), df_mf.columns[0])
male_cols = [c for c in df_mf.columns if "_남_" in c and "세" in c]
age_labels = [c.split("_")[-1] for c in male_cols]
to_int = lambda x: int(str(x).replace(",",""))

def get_province(name: str) -> str:
    m = re.match(r"(.+?(?:특별자치시|특별시|광역시|도))", name)
    return m.group(1) if m else name

# province 컬럼 생성
(df_mf["province"], df_total["province"]) = (df_mf[region_col].apply(get_province), df_total[region_col].apply(get_province))

def get_region_series(df, region_name):
    row = df[df[region_col] == region_name].iloc[0]
    male = [to_int(row[c]) for c in male_cols]
    female = [to_int(row[c.replace("_남_","_여_")]) for c in male_cols]
    return male, female

# ───────────────────────────────────────────
# 페이지 선택
# ───────────────────────────────────────────
page = st.sidebar.radio("페이지 선택", ["인구 피라미드", "성별피라미드 비교", "연령대 피라미드"])

# ───────────────────────────────────────────
# 계층적 지역 선택: 시/도 → 시·군·구
# ───────────────────────────────────────────
provinces = sorted(df_mf["province"].unique())
sel_province = st.sidebar.selectbox("시/도 선택", provinces)
subregions = sorted(df_mf[df_mf["province"] == sel_province][region_col].unique())

# ───────────────────────────────────────────
# 페이지별 피라미드 뷰
# ───────────────────────────────────────────
if page == "인구 피라미드":
    st.header("📈 시·군·구별 인구 피라미드")
    sel_region = st.sidebar.selectbox("시·군·구 선택", subregions)
    male, female = get_region_series(df_mf, sel_region)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=age_labels, x=[-v for v in male], name="남자", orientation='h', text=male))
    fig.add_trace(go.Bar(y=age_labels, x=female, name="여자", orientation='h', text=female))
    fig.update_layout(barmode='overlay', bargap=0.1,
                      title=f"{sel_region} 인구 피라미드",
                      xaxis=dict(title='인구수'), yaxis=dict(title='연령'), height=700)
    st.plotly_chart(fig, use_container_width=True)

elif page == "성별피라미드 비교":
    st.header("📊 여러 지역 성별 피라미드 비교")
    sel_regions = st.sidebar.multiselect("시·군·구 선택", subregions, default=subregions[:2])
    if not sel_regions:
        st.warning("최소 1개 지역을 선택하세요.")
    else:
        for r in sel_regions:
            male, female = get_region_series(df_mf, r)
            fig = go.Figure()
            fig.add_trace(go.Bar(y=age_labels, x=[-v for v in male], name="남자", orientation='h', showlegend=False))
            fig.add_trace(go.Bar(y=age_labels, x=female, name="여자", orientation='h', showlegend=False))
            fig.update_layout(barmode='overlay', bargap=0.1,
                              title=f"{r} 인구 피라미드", xaxis=dict(title='인구수'), yaxis=dict(title='연령'), height=600)
            st.plotly_chart(fig, use_container_width=True)

else:
    st.header("📊 10세 단위 연령대 피라미드")
    sel_region = st.sidebar.selectbox("시·군·구 선택", subregions)
    male, female = get_region_series(df_mf, sel_region)
    ages_num = [int(re.search(r"(\d+)", a).group(1)) for a in age_labels]
    df_age = pd.DataFrame({'age': ages_num, 'male': male, 'female': female})
    bins = list(range(0, 101, 10)) + [200]
    labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    df_age['연령대'] = pd.cut(df_age['age'], bins=bins, labels=labels, right=False)
    df_grp = df_age.groupby('연령대')[['male','female']].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(y=df_grp['연령대'], x=[-v for v in df_grp['male']], name="남자", orientation='h'))
    fig.add_trace(go.Bar(y=df_grp['연령대'], x=df_grp['female'], name="여자", orientation='h'))
    fig.update_layout(barmode='overlay', bargap=0.1,
                      title=f"{sel_region} 10세 연령대 피라미드", xaxis=dict(title='인구수'), yaxis=dict(title='연령대'), height=700)
    st.plotly_chart(fig, use_container_width=True)
