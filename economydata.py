import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io, re

st.set_page_config(page_title="한국 지역별 경제전망 대시보드", layout="wide")
st.title("📈 한국 지역별 경제 발전 & 전망 대시보드 (2021 데이터)")

# --------------- 1. 업로드 -----------------
st.sidebar.header("CSV 3종 업로드")
pop_file  = st.sidebar.file_uploader("① 연령별 인구현황 (2021)", type="csv")
ppi_file  = st.sidebar.file_uploader("② 잠재구매력지수", type="csv")
fert_file = st.sidebar.file_uploader("③ 합계출산율·출생아수", type="csv")

if not (pop_file and ppi_file and fert_file):
    st.info("👈 3개 CSV를 모두 업로드하세요.")
    st.stop()

# --------------- 2. CSV 로더 ---------------

def robust_read_csv(file):
    raw = file.read()
    encodings = ["utf-8-sig","utf-8","cp949","euc-kr"]
    seps = [",",";","|","\t"]
    for enc in encodings:
        for s in seps:
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=s)
                if not df.empty and len(df.columns)>1:
                    return df
            except Exception:
                continue
    return pd.read_csv(io.BytesIO(raw), engine="python")

pop_df, ppi_df, fert_df = map(robust_read_csv, [pop_file, ppi_file, fert_file])
if pop_df.empty or ppi_df.empty or fert_df.empty:
    st.error("❌ 일부 파일이 비어있습니다.")
    st.stop()

# --------------- 3. 지역명 표준화 -----------
CANON = {
    "서울":"서울특별시","서울시":"서울특별시","부산":"부산광역시","대구":"대구광역시","인천":"인천광역시",
    "광주":"광주광역시","대전":"대전광역시","울산":"울산광역시","세종":"세종특별자치시",
    "경기":"경기도","강원":"강원도","충북":"충청북도","충남":"충청남도","전북":"전라북도",
    "전남":"전라남도","경북":"경상북도","경남":"경상남도","제주":"제주특별자치도"
}

def normalize(name:str)->str:
    name=name.strip()
    for k,v in CANON.items():
        if name==k or name.startswith(k):
            return v
    return name

# detect region column in each
def detect_region(df):
    return next((c for c in df.columns if any(k in c for k in ["행정","지역","시군구"])), df.columns[0])

reg_pop  = detect_region(pop_df)
reg_ppi  = detect_region(ppi_df)
reg_fert = detect_region(fert_df)

for df,col in [(pop_df,reg_pop),(ppi_df,reg_ppi),(fert_df,reg_fert)]:
    df[col]=df[col].astype(str).apply(normalize)

# --------------- 4. 인구 지표 계산 ----------
male_cols   = [c for c in pop_df.columns if re.search(r"_남_.*세", c)]
female_cols = [c.replace('_남_','_여_') for c in male_cols]
age_labels  = [c.split('_')[-1] for c in male_cols]
all_cols = male_cols+female_cols
pop_df[all_cols]=pop_df[all_cols].apply(lambda s:s.astype(str).str.replace(',','').astype(int))
work_cols=[c for c in all_cols if 15<=int(re.search(r"(\d{1,3})세",c).group(1))<=64]
pop_df['total_pop']=pop_df[all_cols].sum(axis=1)
pop_df['work_pop']=pop_df[work_cols].sum(axis=1)
pop_df['work_ratio']=pop_df['work_pop']/pop_df['total_pop']*100

# --------------- 5. PPI & TFR 준비 ----------
ppi_val = next((c for c in ppi_df.columns if re.search(r"ppi|구매",c,re.I)), ppi_df.columns[1])
ppi_df = ppi_df[[reg_ppi, ppi_val]].rename(columns={reg_ppi:'region', ppi_val:'PPI'})
ppi_df['PPI']=pd.to_numeric(ppi_df['PPI'],errors='coerce')
ppi_df=ppi_df.groupby('region',as_index=False)['PPI'].mean()

fert_val=next((c for c in fert_df.columns if '합계출산율' in c), fert_df.columns[1])
fert_df=fert_df[[reg_fert,fert_val]].rename(columns={reg_fert:'region',fert_val:'TFR'})
fert_df['TFR']=pd.to_numeric(fert_df['TFR'],errors='coerce')
fert_df=fert_df.groupby('region',as_index=False)['TFR'].mean()

# --------------- 6. 머지 및 지수 ------------
merged=pop_df[[reg_pop,'total_pop','work_ratio']].rename(columns={reg_pop:'region'})
merged=merged.merge(ppi_df,on='region',how='left').merge(fert_df,on='region',how='left')
merged=merged.dropna(subset=['PPI','TFR'])
merged['EDI']=merged['PPI']*(merged['work_ratio']/100)
merged['FDI']=merged['EDI']*merged['TFR']

if merged.empty:
    st.error("❌ 공통 지역 없음 – 파일 지역명을 확인하세요.")
    st.stop()

# --------------- 7. 뷰 선택 -----------------
view=st.sidebar.radio("보기",['지표 표','산점도','피라미드'])

if view=='지표 표':
    st.dataframe(merged.sort_values('EDI',ascending=False).reset_index(drop=True),use_container_width=True)
elif view=='산점도':
    fig=px.scatter(merged,x='EDI',y='FDI',size='total_pop',text='region',labels={'EDI':'EDI','FDI':'FDI','total_pop':'인구'})
    fig.update_traces(textposition='top center')
    st.plotly_chart(fig,use_container_width=True)
else:
    sel_region=st.sidebar.selectbox('피라미드 지역 선택',merged['region'])
    row=pop_df[pop_df[reg_pop].apply(normalize)==sel_region].iloc[0]
    male=[-row[c] for c in male_cols]
    female=[row[c] for c in female_cols]
    fig=go.Figure()
    fig.add_bar(y=age_labels,x=male,name='남자',orientation='h')
    fig.add_bar(y=age_labels,x=female,name='여자',orientation='h')
    fig.update_layout(title=f"{sel_region} 인구 피라미드 (2021)",barmode='overlay',bargap=0.05,height=700,xaxis_title='인구수',yaxis_title='연령')
    st.plotly_chart(fig,use_container_width=True)
