import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import io

# ───────────────────────────────────────────
# 설정
# ───────────────────────────────────────────
st.set_page_config(page_title="인구 피라미드 대시보드", layout="wide")
st.title("📊 인구 피라미드 대시보드 (지역/성별/연령대)")

# ───────────────────────────────────────────
# CSV 파일 업로드
# ───────────────────────────────────────────
st.sidebar.header("CSV 파일 업로드")
mf_file = st.sidebar.file_uploader(
    "남여구분 CSV (예: 202506_연령별인구현현황_월간 남여구분.csv)",
    type="csv"
)
total_file = st.sidebar.file_uploader(
    "합계 CSV (예: 202506_연령별인구현현황_월간 합계.csv)",
    type="csv"
)

# ───────────────────────────────────────────
# 파일 로드
# ───────────────────────────────────────────
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
region_col = next(
    (c for c in df_mf.columns if any(k in c for k in ["행정","지역","시군구"])),
    df_mf.columns[0]
)
male_cols  = [c for c in df_mf.columns if "_남_" in c and "세" in c]
age_labels = [c.split("_")[-1] for c in male_cols]
to_int     = lambda x: int(str(x).replace(",",""))

def get_region_series(df, region_name):
    row = df[df[region_col] == region_name].iloc[0]
    male = [to_int(row[c]) for c in male_cols]
    female = [to_int(row[c.replace("_남_","_여_")]) for c in male_cols]
    return male, female

# ───────────────────────────────────────────
# 페이지 선택: 피라미드, 성별, 연령대
# ───────────────────────────────────────────
page = st.sidebar.radio("페이지 선택", ["인구 피라미드", "성별비교", "연령대비교"])

if page == "인구 피라미드":
    st.header("📈 시·군·구별 인구 피라미드")
    regions = df_mf[region_col].unique().tolist()
    sel_region = st.sidebar.selectbox("시·군·구 선택", regions)
    male, female = get_region_series(df_mf, sel_region)

    # 피라미드 그리기
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=age_labels,
        x=[-v for v in male],
        name="남자",
        orientation='h',
        hovertemplate='남자 %{y}: %{text:,}',
        text=male
    ))
    fig.add_trace(go.Bar(
        y=age_labels,
        x=female,
        name="여자",
        orientation='h',
        hovertemplate='여자 %{y}: %{text:,}',
        text=female
    ))
    fig.update_layout(
        title=f"{sel_region} 인구 피라미드 (2025-06)",
        barmode='overlay',
        bargap=0.1,
        xaxis=dict(tickformat=',d', title='인구수', tickvals=[-max(male),0,max(female)],
                   ticktext=[f"{max(male):,}","0",f"{max(female):,}"]),
        yaxis=dict(title='연령'),
        legend=dict(x=0.1, y=1.1),
        height=700
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "성별비교":
    st.header("📊 시·군·구별 성별 인구 비교")
    regions = df_mf[region_col].unique().tolist()
    sel_regions = st.sidebar.multiselect("시·군·구 선택", regions, default=regions[:2])
    if not sel_regions:
        st.warning("최소 1개 지역을 선택하세요.")
    else:
        data = {'연령': age_labels}
        for r in sel_regions:
            _, female = get_region_series(df_mf, r)
            data[r] = female
        df = pd.DataFrame(data)
        fig = go.Figure()
        for r in sel_regions:
            fig.add_trace(go.Bar(
                x=age_labels,
                y=df[r],
                name=r
            ))
        fig.update_layout(
            title="선택 지역별 여성 인구 비교",
            barmode='group',
            xaxis=dict(title='연령'),
            yaxis=dict(title='인구수',tickformat=',d'),
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.header("📊 10세 단위 연령대별 인구 비교")
    total_counts = [df_total[col].apply(to_int).sum() for col in male_cols]
    ages_num = [int(re.search(r"(\d+)", a).group(1)) for a in age_labels]
    df_age = pd.DataFrame({'age': ages_num, 'count': total_counts})
    bins = list(range(0, 101, 10)) + [200]
    labels = [f"{bins[i]}-{bins[i+1]-1}" for i in range(len(bins)-1)]
    df_age['연령대'] = pd.cut(df_age['age'], bins=bins, labels=labels, right=False)
    df_grp = df_age.groupby('연령대')['count'].sum().reset_index()
    fig = px.line(
        df_grp, x='연령대', y='count', markers=True,
        labels={'count':'인구수','연령대':'연령대'}
    )
    st.plotly_chart(fig, use_container_width=True)
