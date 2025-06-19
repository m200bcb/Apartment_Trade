import pandas as pd
import streamlit as st

st.set_page_config(page_title="아파트 실거래가 하락률 분석기", layout="wide")
st.title("📉 아파트 실거래가 하락률 필터링 도구")
st.markdown("3년간 실거래 데이터를 기반으로 특정 기간 하락률을 기준으로 필터링합니다.")

# 사용자 입력
drop1_threshold = st.slider("3년전→2년전 대비 1년내 평균가 하락률 (drop1)", 0.0, 1.0, 0.3, 0.01)
drop2_threshold = st.slider("3년전→현재 대비 최근 6개월 평균가 하락률 (drop2)", 0.0, 1.0, 0.3, 0.01)

# 매매 파일 경로
paths = {"2023": "2023.csv", "2024": "2024.csv", "2025": "2025.csv"}
columns = ['단지명', '전용면적(㎡)', '거래금액(만원)', '계약년월', '계약일']

# 매매 데이터 로드
dfs = []
for year, path in paths.items():
    df = pd.read_csv(path, encoding='cp949', usecols=columns, on_bad_lines='skip')
    df['연도'] = int(year)
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)
df['거래금액(만원)'] = df['거래금액(만원)'].astype(str).str.replace(",", "").astype(float)
df['계약일자'] = pd.to_datetime(df['계약년월'].astype(str) + df['계약일'].astype(str).str.zfill(2), errors='coerce')

# 구간 정의
cut_3y = pd.to_datetime("2022-06-01")
cut_2y = pd.to_datetime("2023-06-01")
cut_1y = pd.to_datetime("2024-06-01")
cut_6m = pd.to_datetime("2024-12-01")

def get_grouped_avg(start, end):
    sub = df[(df['계약일자'] >= start) & (df['계약일자'] < end)].copy()
    return sub.groupby(['단지명', '전용면적(㎡)'])['거래금액(만원)'].mean().reset_index()

# 매매 평균가 계산
avg_3to2 = get_grouped_avg(cut_3y, cut_2y).rename(columns={'거래금액(만원)': 'avg_3to2'})
avg_1to0 = get_grouped_avg(cut_1y, df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_1to0'})
avg_3to0 = get_grouped_avg(cut_3y, df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_3to0'})
avg_6mo = get_grouped_avg(cut_6m, df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_6mo'})

# 병합 및 하락률 계산
merged = avg_3to2.merge(avg_1to0, on=['단지명', '전용면적(㎡)'], how='inner') \
                 .merge(avg_3to0, on=['단지명', '전용면적(㎡)'], how='inner') \
                 .merge(avg_6mo, on=['단지명', '전용면적(㎡)'], how='inner')

merged['drop1'] = (merged['avg_1to0'] - merged['avg_3to2']) / merged['avg_3to2']
merged['drop2'] = (merged['avg_6mo'] - merged['avg_3to0']) / merged['avg_3to0']

filtered = merged[(merged['drop1'] <= -drop1_threshold) & (merged['drop2'] <= -drop2_threshold)]
filtered = filtered.sort_values(by='drop2').reset_index(drop=True)
filtered.index = filtered.index + 1
filtered['drop1(%)'] = (filtered['drop1'] * 100).round(1)
filtered['drop2(%)'] = (filtered['drop2'] * 100).round(1)

# 전세 데이터 불러오기 및 정제
jeonse = pd.read_csv("2025_j.csv", encoding='cp949', on_bad_lines='skip')
jeonse = jeonse[jeonse['전월세구분'] == '전세'].copy()
jeonse['계약일자'] = pd.to_datetime(jeonse['계약년월'].astype(str) + jeonse['계약일'].astype(str).str.zfill(2), errors='coerce')
jeonse['보증금(만원)'] = jeonse['보증금(만원)'].astype(str).str.replace(",", "").astype(float)

latest = jeonse['계약일자'].max()
cut_1y = pd.to_datetime("2024-06-01")

# 최근 6개월 전세 평균
jeonse_6mo = jeonse[(jeonse['계약일자'] >= cut_6m) & (jeonse['계약일자'] <= latest)]
avg_6mo = jeonse_6mo.groupby(['단지명', '전용면적(㎡)'])['보증금(만원)'].mean().reset_index()
avg_6mo.rename(columns={'보증금(만원)': '전세_6개월_평균가'}, inplace=True)

# 최근 1년 전세 평균
jeonse_1y = jeonse[(jeonse['계약일자'] >= cut_1y) & (jeonse['계약일자'] <= latest)]
avg_1y = jeonse_1y.groupby(['단지명', '전용면적(㎡)'])['보증금(만원)'].mean().reset_index()
avg_1y.rename(columns={'보증금(만원)': '전세_1년_평균가'}, inplace=True)

# 병합
filtered = filtered.merge(avg_6mo, on=['단지명', '전용면적(㎡)'], how='left')
filtered = filtered.merge(avg_1y, on=['단지명', '전용면적(㎡)'], how='left')

# 최종 전세가 컬럼 생성 + 마킹용 컬럼
def get_전세가(row):
    if pd.notna(row['전세_6개월_평균가']):
        return round(row['전세_6개월_평균가'])
    elif pd.notna(row['전세_1년_평균가']):
        return round(row['전세_1년_평균가'])
    else:
        return '-'

def get_하이라이트(row):
    if pd.isna(row['전세_6개월_평균가']) and pd.notna(row['전세_1년_평균가']):
        return True
    return False

filtered['전세가'] = filtered.apply(get_전세가, axis=1)
filtered['전세_노란색'] = filtered.apply(get_하이라이트, axis=1)


# 보기 쉬운 컬럼명 변경
rename_dict = {
    '단지명': '아파트 이름',
    '전용면적(㎡)': '전용면적(㎡)',
    'avg_3to2': '3년 전~2년 전 평균 매매가',
    'avg_1to0': '최근 1년 평균 매매가',
    'avg_3to0': '최근 3년 평균 매매가',
    'avg_6mo': '최근 6개월 평균 매매가',
    'drop1(%)': '최근 1년 하락률(%)',
    'drop2(%)': '최근 6개월 하락률(%)',
    '전세가': '최근 전세가',
}

# 💡 금액을 '1억 5300만' 형식으로 변환하는 함수
def format_price(value):
    if pd.isna(value) or value == '-':
        return '-'
    value = int(round(value))
    if value >= 10000:
        억 = value // 10000
        만 = value % 10000
        if 만 == 0:
            return f"{억}억"
        return f"{억}억 {만}만"
    else:
        return f"{value}만"

# ✅ 적용할 컬럼
money_cols = ['3년 전~2년 전 평균 매매가', '최근 1년 평균 매매가', '최근 3년 평균 매매가',
              '최근 6개월 평균 매매가', '최근 전세가']


# 컬럼명 변경
filtered_renamed = filtered.rename(columns=rename_dict)

# 문자열 포맷 적용
for col in money_cols:
    if col in filtered_renamed.columns:
        filtered_renamed[col] = filtered_renamed[col].apply(format_price)

# 최종 표시할 컬럼만 추림
display_cols = list(rename_dict.values())
data_to_show = filtered_renamed[display_cols]

# 하이라이트 함수 (열 개수에 맞춰 반환)
def highlight_jeonse(row):
    return ['background-color: yellow' if col == '최근 전세가' and pd.isna(row['최근 6개월 평균 매매가']) and row['최근 전세가'] != '-' else '' for col in display_cols]

# 출력
st.subheader("📋 필터링된 결과")
st.write(f"선택 기준: drop1 ≤ -{int(drop1_threshold * 100)}%, drop2 ≤ -{int(drop2_threshold * 100)}%")

styled = data_to_show.style.apply(highlight_jeonse, axis=1)
st.dataframe(styled, use_container_width=True)
