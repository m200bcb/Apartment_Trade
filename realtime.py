import pandas as pd
import streamlit as st
import datetime
import requests
from io import BytesIO
from bs4 import BeautifulSoup

st.set_page_config(page_title="아파트 실거래가 하랑률 분석기", layout="wide")
st.title("📉 아파트 실거래가 하랑률 필터링 도구 (크롤링 자동 반영)")
st.markdown("3년간 실거래 데이터를 기반으로 특정 기간 하랑률을 기준으로 필터링합니다. CSV 자동 수집 기능이 포함되어 있습니다.")

# 사용자 입력
sido_dict = {
    '서울특별시': '11', '부산광역시': '26', '대구광역시': '27', '인천광역시': '28',
    '광주광역시': '29', '대전광역시': '30', '울산광역시': '31', '세종특별자치시': '36',
    '경기도': '41', '강원특별자치도': '51', '충청북도': '43', '충청남도': '44',
    '전라북도': '45', '전라남도': '46', '경상북도': '47', '경상남도': '48', '제주특별자치도': '50'
}

st.sidebar.header("🔍 지역 및 옵션 선택")
sido_name = st.sidebar.selectbox("시도 선택", list(sido_dict.keys()))
deal_type = st.sidebar.radio("거래 유형 선택", ["매매", "전세"])

# 시군구 정보 가져오기
def get_sgg_list(sido_code):
    url = "https://rt.molit.go.kr/sggAjax.do"
    data = {
    'menuGubun': 'A',
    'gubunCode': 'APT',   # 기존 'LAND'에서 'APT'로 변경
    'sidoCode': sido_code
    }
    headers = {
        'Referer': 'https://rt.molit.go.kr/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    res = requests.post(url, data=data, headers=headers)
    print(res.text)
    soup = BeautifulSoup(res.text, 'html.parser')

    if "찾을 수가 없습니다" in soup.text:
        st.error("시군구 데이터를 가져오지 못했습니다. 요청 조건을 확인하세요.")
        st.stop()

    # 이제 안전하게 처리
    table = soup.find("table")
    if table is None:
        st.error("시군구 목록을 찾을 수 없습니다. 서버 구조가 변경되었을 수 있습니다.")
        st.stop()

    df = pd.read_html(str(table))[0]
    return dict(zip(df[0], df[1]))


sido_code = sido_dict[sido_name]
sgg_dict = get_sgg_list(sido_code)
sgg_name = st.sidebar.selectbox("시군구 선택", list(sgg_dict.keys()))
sgg_code = sgg_dict[sgg_name]


drop1_threshold = st.slider("3년전→2년전 대비 1년내 평균가 하랑률 (drop1)", 0.0, 1.0, 0.3, 0.01)
drop2_threshold = st.slider("3년전→현재 대비 최근 6개월 평균가 하랑률 (drop2)", 0.0, 1.0, 0.3, 0.01)

# CSV 다운로드 함수
@st.cache_data(show_spinner=False)
def download_data(year: int, deal_type: str):
    month = "12"  # 월 건 가장 날짜가 많은 것으로 고정
    deal_code = "A1" if deal_type == "매매" else "B1"

    url = (
        f"https://rt.molit.go.kr/new/gis/getDanjiCSV.do?"
        f"menuGubun=A&gubunCode=LAND&dealYM={year}{month}&"
        f"sidoCode={sido_code}&sggCode={sgg_code}&danjiCode=&dealType={deal_code}"
    )

    headers = {'Referer': 'https://rt.molit.go.kr/'}
    r = requests.get(url, headers=headers)
    r.encoding = 'euc-kr'
    df = pd.read_csv(BytesIO(r.content), encoding='cp949')
    df["연도"] = year
    return df

# 최근 3년간 데이터 수집
years = [2023, 2024, 2025]
dfs = []
for y in years:
    try:
        df = download_data(y, deal_type)
        dfs.append(df)
    except Exception:
        st.warning(f"{y}년 {deal_type} 데이터를 불러오는 데 실패했습니다.")

if not dfs:
    st.error("데이터를 불러올 수 없습니다.")
    st.stop()

# 전체 데이터 조합
all_df = pd.concat(dfs, ignore_index=True)
all_df = all_df[all_df['계약년월'].notna()]
all_df['계약일자'] = pd.to_datetime(all_df['계약년월'].astype(int).astype(str) + all_df['계약일'].astype(str).str.zfill(2), errors='coerce')
all_df['거래금액(만원)'] = all_df['거래금액(만원)'].astype(str).str.replace(",", "").astype(float)

# 기준 날짜
cut_3y = pd.to_datetime("2022-06-01")
cut_2y = pd.to_datetime("2023-06-01")
cut_1y = pd.to_datetime("2024-06-01")
cut_6m = pd.to_datetime("2024-12-01")

# 평균가 계산
def get_grouped_avg(start, end):
    sub = all_df[(all_df['계약일자'] >= start) & (all_df['계약일자'] < end)].copy()
    return sub.groupby(['단지명', '전용면적(㎡)'])['거래금액(만원)'].mean().reset_index()

avg_3to2 = get_grouped_avg(cut_3y, cut_2y).rename(columns={'거래금액(만원)': 'avg_3to2'})
avg_1to0 = get_grouped_avg(cut_1y, all_df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_1to0'})
avg_3to0 = get_grouped_avg(cut_3y, all_df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_3to0'})
avg_6mo = get_grouped_avg(cut_6m, all_df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_6mo'})

merged = avg_3to2.merge(avg_1to0, on=['단지명', '전용면적(㎡)'], how='inner') \
                 .merge(avg_3to0, on=['단지명', '전용면적(㎡)'], how='inner') \
                 .merge(avg_6mo, on=['단지명', '전용면적(㎡)'], how='inner')

merged['drop1'] = (merged['avg_1to0'] - merged['avg_3to2']) / merged['avg_3to2']
merged['drop2'] = (merged['avg_6mo'] - merged['avg_3to0']) / merged['avg_3to0']

filtered = merged[(merged['drop1'] <= -drop1_threshold) & (merged['drop2'] <= -drop2_threshold)]
filtered = filtered.sort_values(by='drop2').reset_index(drop=True)
filtered.index += 1
filtered['drop1(%)'] = (filtered['drop1'] * 100).round(1)
filtered['drop2(%)'] = (filtered['drop2'] * 100).round(1)

# 평균가 형식 포맷화
def format_price(value):
    if pd.isna(value): return "-"
    value = int(round(value))
    if value >= 10000:
        어깨 = value // 10000
        만 = value % 10000
        return f"{어깨}억 {만}만" if 만 else f"{어깨}억"
    return f"{value}만"

rename_dict = {
    '단지명': '아파트 이름',
    '전용면적(㎡)': '전용면적(㎡)',
    'avg_3to2': '3년 전~2년 전 평균 매매가',
    'avg_1to0': '최근 1년 평균 매매가',
    'avg_3to0': '최근 3년 평균 매매가',
    'avg_6mo': '최근 6개월 평균 매매가',
    'drop1(%)': '최근 1년 하락률(%)',
    'drop2(%)': '최근 6개월 하락률(%)'
}

money_cols = list(rename_dict.values())[:-2]
filtered = filtered.rename(columns=rename_dict)
for col in money_cols:
    filtered[col] = filtered[col].apply(format_price)

st.subheader("📋 필터링된 결과")
st.write(f"선택 기준: drop1 ≤ -{int(drop1_threshold * 100)}%, drop2 ≤ -{int(drop2_threshold * 100)}%")
st.dataframe(filtered[list(rename_dict.values()) + ['최근 1년 하락률(%)', '최근 6개월 하락률(%)']], use_container_width=True)