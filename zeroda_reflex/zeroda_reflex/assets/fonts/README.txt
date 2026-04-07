한글 폰트 배치 안내
====================

PDF 생성(월말명세서)에 한글 폰트가 필요합니다.
아래 중 하나의 폰트 파일을 이 폴더에 배치하세요.

권장: NanumGothic.ttf
-------------------------------
1. https://hangeul.naver.com/font 접속
2. "나눔고딕" 다운로드 및 설치
3. 설치된 폰트 위치에서 NanumGothic.ttf 파일을 복사
   - Windows 설치 경로: C:\Windows\Fonts\NanumGothic.ttf
   - Linux: /usr/share/fonts/truetype/nanum/NanumGothic.ttf
4. 이 폴더(zeroda_reflex/zeroda_reflex/assets/fonts/)에 붙여넣기

또는, 서버(Linux)에서 자동 설치:
  sudo apt-get install -y fonts-nanum
  → /usr/share/fonts/truetype/nanum/NanumGothic.ttf 에 자동 설치됨
  → 이 경우 이 폴더에 복사하지 않아도 됩니다.

Windows 개발 환경:
  - C:\Windows\Fonts\malgun.ttf (맑은 고딕) 이 있으면 자동 인식됩니다.
  - 별도 복사 불필요.

폰트 탐색 우선순위 (pdf_generator.py):
  1) zeroda_reflex/zeroda_reflex/assets/fonts/NanumGothic.ttf  (이 폴더)
  2) C:/Windows/Fonts/malgun.ttf
  3) /usr/share/fonts/truetype/nanum/NanumGothic.ttf
