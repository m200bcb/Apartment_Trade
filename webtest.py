import requests

url = "https://rt.molit.go.kr/pt/xls/xls.do?mobileAt="

headers = {
    "Referer": "https://rt.molit.go.kr/new/gis/openSimpleMap.do",
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}

# 예시 POST 데이터 (필요한 실제 파라미터로 변경해야 함)
data = {
    "someParameter": "someValue",
    # 여기에 실제 필요한 파라미터 키-값을 넣어야 함
}

response = requests.post(url, headers=headers, data=data)

if response.headers.get('Content-Type') == 'application/vnd.ms-excel':
    with open("output.xls", "wb") as f:
        f.write(response.content)
    print("엑셀 파일 다운로드 성공")
else:
    print("엑셀 파일이 아닙니다. 응답 헤더:", response.headers)
    print(response.text)  # 에러 메시지 확인용
