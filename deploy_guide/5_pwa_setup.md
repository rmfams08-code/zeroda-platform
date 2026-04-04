# PWA 설정 가이드 (기사앱 모바일 설치)

## 1. nginx 설정 추가

서버에 SSH 접속 후 nginx 설정 파일을 수정합니다.

```bash
ssh root@223.130.131.188
nano /etc/nginx/sites-available/zeroda
```

기존 `location /` 블록 **위에** 다음 블록을 추가합니다:

```nginx
# ── PWA 정적 파일 서빙 ──
location /static/ {
    alias /opt/zeroda-platform/static/;
    expires 7d;
    add_header Cache-Control "public, immutable";
}

# ── Service Worker (루트 스코프 필요) ──
location /service-worker.js {
    alias /opt/zeroda-platform/static/service-worker.js;
    add_header Service-Worker-Allowed "/";
    expires -1;
}
```

설정 적용:
```bash
nginx -t && systemctl restart nginx
```

## 2. GitHub 업로드 + 서버 반영

로컬에서 수정한 파일들을 GitHub에 올린 후:

```bash
ssh root@223.130.131.188
cd /opt/zeroda-platform && git pull && systemctl restart zeroda
```

### 업로드할 파일 목록:
- `main.py` (PWA 메타태그 추가)
- `modules/driver/dashboard.py` (안전점검 1회 제한 + 미완료 삭제)
- `static/manifest.json` (신규)
- `static/service-worker.js` (신규)
- `static/offline.html` (신규)
- `static/icons/icon-192.png` (신규)
- `static/icons/icon-512.png` (신규)

## 3. 기사님 안내 방법

### Android (삼성, LG 등)
1. Chrome 브라우저로 `https://zeroda.co.kr` 접속
2. 기사 계정으로 로그인
3. 주소줄 오른쪽 ⋮ (점 세개) 메뉴 클릭
4. **"홈 화면에 추가"** 선택
5. 앱 이름 확인 후 **"추가"** 클릭
6. 홈화면에 ZERODA 아이콘이 생성됨 → 터치하면 앱처럼 실행

### iPhone / iPad (iOS)
1. Safari 브라우저로 `https://zeroda.co.kr` 접속
2. 기사 계정으로 로그인
3. 하단 공유 버튼 (□↑) 클릭
4. **"홈 화면에 추가"** 선택
5. 앱 이름 확인 후 **"추가"** 클릭
6. 홈화면에 ZERODA 아이콘이 생성됨

### 특징
- 별도 앱스토어 다운로드 불필요
- 상단 주소줄 없이 전체 화면으로 실행
- 앱 아이콘 + 앱 이름 표시
- 인터넷 연결 필요 (오프라인 시 안내 페이지 표시)

## 4. 확인 방법

브라우저 개발자도구(F12) > Application > Manifest 에서
manifest.json이 정상 로딩되는지 확인합니다.
