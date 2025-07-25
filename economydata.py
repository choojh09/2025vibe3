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
st.title("📈 한국 지역별 경제 발전 & 전망 대시보드 (2021 데이터)")

# --------------------------------------------------------------------------------
# 1. CSV 업로드 위젯
# --------------------------------------------------------------------------------
st.sidebar.header("CSV 3종 업로드")
col_up = st.sidebar.container()
pop_file  = col_up.file_uploader("① 연령별 인구현황 (2021)", type="csv", key="pop")
ppi_file  = col_up.file_uploader("② 잠재구매력지수", type="csv", key="ppi")
fert_file = col_up.file_uploader("③ 합계출산율·출생아수", type="csv", key="fert")

if not (pop_file and ppi_file and fert_file):
    st.info("👈 3개 CSV 파일을 모두 업로드하면 대시보드가 표시됩니다.")
    st.stop()

# --------------------------------------------------------------------------------
# 2. 안전한 CSV 로더 (다중 인코딩 & 구분자 탐색)
# --------------------------------------------------------------------------------

def robust_read_csv(uploaded_file):
    """Try multiple encodings & delimiters until DataFrame is non‑empty."""
    raw = uploaded_file.read()
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr", "ISO-8859-1"]
    seps      = [",", ";", "|", "\t"]
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=sep)
                if not df.empty and len(df.columns) > 1:
                    return df
            except (UnicodeDecodeError, pd.errors.EmptyDataError):
                continue
    # 마지막 시도: pandas 자동 추정
    return pd.read_csv(io.BytesIO(raw), engine="python")

pop_df  = robust_read_csv(pop_file)
ppi_df  = robust_read_csv(ppi_file)
fert_df = robust_read_csv(fert_file)

# 필수 컬럼 체크
if pop_df.empty or ppi_df.empty or fert_df.empty:
    st.error("❌ 일부 파일이 비어 있거나 형식을 파악할 수 없습니다. CSV 내용을 확인해주세요.")
    st.stop()

# --------------------------------------------------------------------------------
# 3. 전처리 및 지수 계산
# --------------------------------------------------------------------------------
region_col = next((c for c in pop_df.columns if any(k in c for k in ["행정", "지역", "시군구"])), pop_df.columns[0])
# 연령별 숫자 컬럼
male_cols = [c for c in pop_df.columns if re.search(r"_남_.*세", c)]
female_cols = [c.replace('_남_', '_여_') for c in male_cols]
age_labels = [c.split('_')[-1] for c in male_cols]
all_age_cols = male_cols + female_cols
pop_df[all_age_cols] = pop_df[all_age_cols].apply(lambda col: col.astype(str).str.replace(',', '').astype(int))
# 가동연령 15~64세
work_cols = [c for c in all_age_cols if 15 <= int(re.search(r"(\d{1,3})세", c).group(1)) <= 64]

pop_df['total_pop']  = pop_df[all_age_cols].sum(axis=1)
pop_df['work_pop']   = pop_df[work_cols].sum(axis=1)
pop_df['work_ratio'] = pop_df['work_pop'] / pop_df['total_pop'] * 100

# PPI, TFR 전처리 & 중복 처리
ppi_region = next((c for c in ppi_df.columns if '지역' in c or '행정' in c), ppi_df.columns[0])
ppi_value  = next((c for c in ppi_df.columns if re.search(r"ppi|PPI|구매", c, re.I)), ppi_df.columns[1])
ppi_df = ppi_df[[ppi_region, ppi_value]].rename(columns={ppi_region: region_col, ppi_value: 'PPI'})
ppi_df[region_col] = ppi_df[region_col].astype(str).str.strip()
ppi_df['PPI'] = pd.to_numeric(ppi_df['PPI'], errors='coerce')
ppi_df = ppi_df.groupby(region_col, as_index=False)['PPI'].mean()

fert_region = next((c for c in fert_df.columns if '지역' in c or '행정' in c), fert_df.columns[0])
fert_value  = next((c for c in fert_df.columns if '합계출산율' in c), fert_df.columns[1])
fert_df = fert_df[[fert_region, fert_value]].rename(columns={fert_region: region_col, fert_value: 'TFR'})
fert_df[region_col] = fert_df[region_col].astype(str).str.strip()
fert_df['TFR'] = pd.to_numeric(fert_df['TFR'], errors='coerce')
fert_df = fert_df.groupby(region_col, as_index=False)['TFR'].mean()

# 머지 및 지수 계산
merged = pop_df[[region_col, 'total_pop', 'work_ratio']].copy()
merged[region_col] = merged[region_col].astype(str).str.strip()
merged = merged.merge(ppi_df, on=region_col, how='inner').merge(fert_df, on=region_col, how='inner')
merged = pop_df[[region_col, 'total_pop', 'work_ratio']].merge(ppi_df, on=region_col, how='inner').merge(fert_df, on=region_col, how='inner')
merged = merged.dropna(subset=['PPI', 'TFR'])
merged['EDI'] = merged['PPI'] * (merged['work_ratio'] / 100)
merged['FDI'] = merged['EDI'] * merged['TFR']

# --------------------------------------------------------------------------------
# 4. 대시보드 뷰 선택
# --------------------------------------------------------------------------------
view = st.sidebar.radio("보기", ["지표 표", "EDI/FDI 산점도", "인구 피라미드"])

if view == "지표 표":
    st.subheader("📊 지역별 경제 지표 표")
    st.dataframe(merged.sort_values('EDI', ascending=False).reset_index(drop=True), use_container_width=True)

elif view == "EDI/FDI 산점도":
    fig = px.scatter(merged, x='EDI', y='FDI', size='total_pop', text=region_col,
                     labels={'EDI':'경제발전지수(EDI)', 'FDI':'미래전망지수(FDI)', 'total_pop':'인구수'})
    fig.update_traces(textposition='top center')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🏆 EDI Top 5 / Bottom 5")
    c1, c2 = st.columns(2)
    with c1:
        st.write("### Top 5")
        st.table(merged.nlargest(5, 'EDI')[ [region_col, 'EDI'] ])
    with c2:
        st.write("### Bottom 5")
        st.table(merged.nsmallest(5, 'EDI')[ [region_col, 'EDI'] ])

else:  # 인구 피라미드
    regions = pop_df[region_col].unique().tolist()
    sel_region = st.sidebar.selectbox("피라미드 지역 선택", regions)
    row = pop_df[pop_df[region_col] == sel_region].iloc[0]
    male_vals   = [-row[c] for c in male_cols]
    female_vals = [row[c] for c in female_cols]
    fig = go.Figure()
    fig.add_bar(y=age_labels, x=male_vals, name='남자', orientation='h')
    fig.add_bar(y=age_labels, x=female_vals, name='여자', orientation='h')
    fig.update_layout(title=f"{sel_region} 인구 피라미드 (2021)", barmode='overlay', bargap=0.05,
                      xaxis=dict(title='인구수'), yaxis=dict(title='연령'), height=700)
    st.plotly_chart(fig, use_container_width=True)
