import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import re

# --------------------------------------------------------------------------------
# Streamlit 설정
# --------------------------------------------------------------------------------
st.set_page_config(page_title="한국 지역별 경제전망 대시보드", layout="wide")
st.title("📈 한국 지역별 경제 발전 & 전망 대시보드 (2021 기준)")

# --------------------------------------------------------------------------------
# 1) CSV 파일 업로드 위젯
# --------------------------------------------------------------------------------
st.sidebar.header("CSV 파일 업로드 (3종)")
col_upload = st.sidebar.container()

pop_file   = col_upload.file_uploader("① 2021 연령별 인구현황 (CSV)", type="csv", key="pop")
ppi_file   = col_upload.file_uploader("② 잠재구매력지수 (CSV)",        type="csv", key="ppi")
fert_file  = col_upload.file_uploader("③ 지역별 합계출산율·출생아수 (CSV)", type="csv", key="fert")

if not (pop_file and ppi_file and fert_file):
    st.info("왼쪽에서 3개 CSV 모두 업로드하면 대시보드가 표시됩니다.")
    st.stop()

# --------------------------------------------------------------------------------
# 2) 데이터 로드
# --------------------------------------------------------------------------------

def load_csv(file, encoding="cp949"):
    try:
        return pd.read_csv(io.BytesIO(file.read()), encoding=encoding)
    except UnicodeDecodeError:
        return pd.read_csv(io.BytesIO(file.read()), encoding="utf-8")

pop_df  = load_csv(pop_file)
ppi_df  = load_csv(ppi_file, encoding="utf-8")
fert_df = load_csv(fert_file)

# --------------------------------------------------------------------------------
# 3) 전처리 & 지표 계산
# --------------------------------------------------------------------------------
# (1) 인구 데이터: '행정구역' / 각 연령별 인구 칼럼 존재 가정
region_col = next((c for c in pop_df.columns if any(k in c for k in ["행정", "지역", "시군구"])), pop_df.columns[0])

# 가동연령(15-64세) 비율 계산
work_cols = [c for c in pop_df.columns if re.search(r"_(\d{2})세", c) and 15 <= int(re.search(r"(\d{2})세", c).group(1)) <= 64]
total_cols= [c for c in pop_df.columns if re.search(r"세$", c)]

pop_df["total_pop"]      = pop_df[total_cols].apply(lambda r: r.str.replace(',', '').astype(int).sum(), axis=1)
pop_df["work_pop"]       = pop_df[work_cols].apply(lambda r: r.str.replace(',', '').astype(int).sum(), axis=1)
pop_df["work_ratio"]     = pop_df["work_pop"] / pop_df["total_pop"] * 100  # %

# (2) PPI 데이터: region, ppi
ppi_region_col = next((c for c in ppi_df.columns if '지역' in c or '행정' in c), ppi_df.columns[0])
ppi_val_col    = next((c for c in ppi_df.columns if re.search(r"ppi|PPI|구매", c, re.I)), ppi_df.columns[1])
ppi_df = ppi_df[[ppi_region_col, ppi_val_col]].rename(columns={ppi_region_col: region_col, ppi_val_col: "PPI"})

# (3) Fertility 데이터: region, 합계출산율
fert_region_col = next((c for c in fert_df.columns if '지역' in c or '행정' in c), fert_df.columns[0])
fert_rate_col   = next((c for c in fert_df.columns if '합계출산율' in c), fert_df.columns[1])

fert_df = fert_df[[fert_region_col, fert_rate_col]].rename(columns={fert_region_col: region_col, fert_rate_col: "TFR"})

# (4) 머지 및 지수 계산
merged = pop_df[[region_col, "total_pop", "work_ratio"]].merge(ppi_df, on=region_col, how='inner').merge(fert_df, on=region_col, how='inner')
merged['PPI'] = pd.to_numeric(merged['PPI'], errors='coerce')
merged['TFR'] = pd.to_numeric(merged['TFR'], errors='coerce')

# 경제발전지수 (EDI) 가정: EDI = PPI * (work_ratio/100)
merged['EDI'] = merged['PPI'] * (merged['work_ratio']/100)
# 미래전망지수 (FDI) 가정: FDI = EDI * TFR
merged['FDI'] = merged['EDI'] * merged['TFR']

# --------------------------------------------------------------------------------
# 4) 대시보드 UI
# --------------------------------------------------------------------------------
page = st.sidebar.radio("대시보드 뷰", ["개요", "지역 비교 그래프", "인구 피라미드"])

if page == "개요":
    st.subheader("📊 지역별 지표 요약")
    st.dataframe(merged.sort_values('EDI', ascending=False).reset_index(drop=True), use_container_width=True)

elif page == "지역 비교 그래프":
    st.subheader("🔍 경제발전지수(EDI) vs 미래전망지수(FDI)")
    fig = px.scatter(
        merged, x="EDI", y="FDI", size="total_pop", text=region_col,
        hover_data={region_col:True, "total_pop":":,", "work_ratio":".2f", "TFR":".2f"},
        labels={"EDI":"경제발전지수(EDI)", "FDI":"미래전망지수(FDI)", "total_pop":"인구수"}
    )
    fig.update_traces(textposition='top center')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📈 상위·하위 지역 막대 그래프")
    top5 = merged.nlargest(5, 'EDI')
    bottom5 = merged.nsmallest(5, 'EDI')
    fig2 = px.bar(top5, x='EDI', y=region_col, orientation='h', color='EDI', title='EDI Top 5')
    fig3 = px.bar(bottom5, x='EDI', y=region_col, orientation='h', color='EDI', title='EDI Bottom 5')
    st.plotly_chart(fig2, use_container_width=True)
    st.plotly_chart(fig3, use_container_width=True)

else:  # 인구 피라미드
    regions = merged[region_col].tolist()
    sel_region = st.selectbox("피라미드 볼 지역 선택", regions)
    male_cols_full   = [c for c in pop_df.columns if "_남_" in c and c.endswith('세')]
    female_cols_full = [c.replace('_남_', '_여_') for c in male_cols_full]
    row_pop = pop_df[pop_df[region_col] == sel_region].iloc[0]
    male_vals   = [-int(str(row_pop[c]).replace(',', '')) for c in male_cols_full]
    female_vals = [int(str(row_pop[c]).replace(',', '')) for c in female_cols_full]
    ages = [c.split('_')[-1] for c in male_cols_full]

    fig = go.Figure()
    fig.add_bar(y=ages, x=male_vals, name='남자', orientation='h')
    fig.add_bar(y=ages, x=female_vals, name='여자', orientation='h')
    fig.update_layout(title=f"{sel_region} 인구 피라미드 (2021)", barmode='overlay', bargap=0.05,
                      xaxis=dict(title='인구수'), yaxis=dict(title='연령'), height=700)
    st.plotly_chart(fig, use_container_width=True)
