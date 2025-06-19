import pandas as pd

# 1. 파일 경로 지정
paths = {
    "2023": "2023.csv",
    "2024": "2024.csv",
    "2025": "2025.csv"
}


# 2. 필요한 열
columns = ['단지명', '전용면적(㎡)', '거래금액(만원)', '계약년월', '계약일']

# 3. 파일 로드 및 통합
dfs = []
for year, path in paths.items():
    df = pd.read_csv(path, encoding='cp949', usecols=columns, on_bad_lines='skip')
    df['연도'] = int(year)
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)

# 4. 데이터 정제
df['거래금액(만원)'] = df['거래금액(만원)'].astype(str).str.replace(",", "").astype(float)
df['계약일자'] = pd.to_datetime(df['계약년월'].astype(str) + df['계약일'].astype(str).str.zfill(2), errors='coerce')

# 5. 구간 정의
cut_3y = pd.to_datetime("2022-06-01")
cut_2y = pd.to_datetime("2023-06-01")
cut_1y = pd.to_datetime("2024-06-01")
cut_6m = pd.to_datetime("2024-12-01")

# 6. 평균가 계산 함수
def get_grouped_avg(start, end):
    sub = df[(df['계약일자'] >= start) & (df['계약일자'] < end)].copy()
    return sub.groupby(['단지명', '전용면적(㎡)'])['거래금액(만원)'].mean().reset_index()

# 7. 구간별 평균가 추출
avg_3to2 = get_grouped_avg(cut_3y, cut_2y).rename(columns={'거래금액(만원)': 'avg_3to2'})
avg_1to0 = get_grouped_avg(cut_1y, df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_1to0'})
avg_3to0 = get_grouped_avg(cut_3y, df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_3to0'})
avg_6mo = get_grouped_avg(cut_6m, df['계약일자'].max()).rename(columns={'거래금액(만원)': 'avg_6mo'})

# 8. 병합
merged = avg_3to2.merge(avg_1to0, on=['단지명', '전용면적(㎡)'], how='inner') \
                 .merge(avg_3to0, on=['단지명', '전용면적(㎡)'], how='inner') \
                 .merge(avg_6mo, on=['단지명', '전용면적(㎡)'], how='inner')

# 9. 하락률 계산
merged['drop1'] = (merged['avg_1to0'] - merged['avg_3to2']) / merged['avg_3to2']
merged['drop2'] = (merged['avg_6mo'] - merged['avg_3to0']) / merged['avg_3to0']

# 10. 조건 필터링: 두 조건 모두 -30% 이상 하락
filtered = merged[(merged['drop1'] <= -0.2) & (merged['drop2'] <= -0.2)]

# 11. 전체 행 출력 설정 + 인덱스 리셋 및 1부터 시작
pd.set_option('display.max_rows', None)
filtered = filtered.sort_values(by='drop2').reset_index(drop=True)
filtered.index = filtered.index + 1  # 인덱스 1부터 시작

# 12. 출력
print(filtered)