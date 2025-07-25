import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

st.set_page_config(page_title="인구 시각화 대시보드", layout="wide")
st.title("📊 2025‑06 서울특별시 인구 시각화")

# ───────────────────────────────────────────
# 0. 파일 업로드
# ───────────────────────────────────────────
st.sidebar.header("⬆️ CSV 업로드")
mf_file   = st.sidebar.file_uploader("남여구분 CSV (예: …남여구분.csv)",
                                     type=["csv"], key="mf")
total_file = st.sidebar.file_uploader("합계 CSV (예: …합계.csv)",
                                      type=["csv"], key="total")

# 도우미: CSV → DataFrame (cp949)
def load_csv(uploaded_file):
    if uploaded_file is None:
        return None
    # 업로드 객체를 바이너리 → 텍스트IO로 변환
    return pd.read_csv(
        io.BytesIO(uploaded_file.read()),
        encoding="cp949"
    )

df_mf    = load_csv(mf_file)
df_total = load_csv(total_file)

# ───────────────────────────────────────────
# 1. 데이터 준비 & 지역 선택
# ───────────────────────────────────────────
if df_mf is not None and df_total is not None:

    # '행정구역' 또는 비슷한 열 이름을 감지
    region_col = [c for c in df_mf.columns if "행정" in c or "지역" in c or "시군구" in c]
    region_col = region_col[0] if region_col else df_mf.columns[0]

    regions = df_mf[region_col].tolist()
    default_region = regions[0]  # 예: 서울특별시 합계

    sel_region = st.sidebar.selectbox("📍 시·군·구 선택", regions, index=0)

    # 선택 행 추출
    row_mf    = df_mf[df_mf[region_col] == sel_region].iloc[0]
    row_total = df_total[df_total[region_col] == sel_region].iloc[0]

    # 연령 컬럼 파싱
    male_cols = [c for c in df_mf.columns if "_남_" in c and "세" in c]
    ages      = [c.split('_')[-1] for c in male_cols]

    def to_int(x):
        return int(str(x).replace(",", ""))

    # 피라미드용 값
    male_vals   = [-to_int(row_mf[c]) for c in male_cols]
    female_vals = [ to_int(row_mf[c.replace("_남_", "_여_")]) for c in male_cols]

    # 합계용 값
    total_cols = [c for c in df_total.columns if "_계_" in c and "세" in c]
    total_ages = [c.split('_')[-1] for c in total_cols]
    total_vals = [to_int(row_total[c]) for c in total_cols]

    # ───────────────────────────────────────
    # 2. Plotly 시각화
    # ───────────────────────────────────────
    # (1) 인구 피라미드
    fig_pyr = go.Figure()
    fig_pyr.add_bar(y=ages, x=male_vals, name="남자", orientation="h",
                    hovertemplate="남자 %{y}: %{text:,}<extra></extra>",
                    text=[abs(v) for v in male_vals])
    fig_pyr.add_bar(y=ages, x=female_vals, name="여자", orientation="h",
                    hovertemplate="여자 %{y}: %{text:,}<extra></extra>",
                    text=female_vals)

    fig_pyr.update_layout(
        title=f"{sel_region} 연령별 인구 피라미드 (2025‑06)",
        barmode="overlay",
        bargap=0.05,
        xaxis_title="인구수",
        yaxis_title="연령",
        xaxis=dict(tickformat=",d"),
        legend_title_text="성별",
        height=800
    )

    # (2) 총 인구 막대그래프
    fig_total = go.Figure()
    fig_total.add_bar(x=total_ages, y=total_vals,
                      hovertemplate="%{x}: %{y:,}<extra></extra>")

    fig_total.update_layout(
        title=f"{sel_region} 연령별 총인구수 (2025‑06)",
        xaxis_title="연령",
        yaxis_title="인구수",
        xaxis_tickangle=-45,
        yaxis=dict(tickformat=",d"),
        height=600
    )

    # ───────────────────────────────────────
    # 3. 화면 배치
    # ───────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_pyr, use_container_width=True)
    with col2:
        st.plotly_chart(fig_total, use_container_width=True)

    # 데이터 미리보기
    with st.expander("📑 원본 데이터 보기"):
        st.write("남/여 구분 데이터 (선택 지역 행):")
        st.dataframe(row_mf.to_frame().T, use_container_width=True)
        st.write("합계 데이터 (선택 지역 행):")
        st.dataframe(row_total.to_frame().T, use_container_width=True)

else:
    st.info("왼쪽 사이드바에서 두 개의 CSV 파일을 모두 업로드하면 시각화가 표시됩니다.")
    st.markdown("""
    **필요한 파일 예시**

    1. `202506_202506_연령별인구현황_월간 남여구분.csv`  
    2. `202506_202506_연령별인구현황_월간 합계.csv`

    업로드 후, 시·군·구를 선택하면 그래프가 나타납니다.
    """)
