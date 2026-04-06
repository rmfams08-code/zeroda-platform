# ZERODA Reflex 서버 배포 가이드
> zeroda.co.kr → Reflex 단독 운영 (Streamlit 교체)

---

## 서버 정보

| 항목 | 내용 |
|---|---|
| 서버 | zeroda-web (네이버클라우드 KVM) |
| 공인 IP | 223.130.131.188 |
| 도메인 | zeroda.co.kr |
| 접속 | root |
| **Reflex 경로** | **/opt/zeroda-reflex** |
| **Reflex 포트** | **프론트 3000 / 백엔드 8000** |
| DB | /opt/zeroda-platform/zeroda.db |
| SSL | Let's Encrypt (자동갱신) |

---

## 배포 절차 (서버에서 실행)

### 1. 서버 접속
```bash
ssh root@223.130.131.188
```

### 2. 자동 설치 (setup.sh)
```bash
cd /opt/zeroda-platform && git pull
bash zeroda_reflex/deploy/setup.sh
```

### 3. 환경변수 설정
```bash
nano /opt/zeroda-reflex/.env
```
각 항목에 실제 API 키를 입력합니다.

### 4. Reflex 초기화 + 빌드
```bash
cd /opt/zeroda-reflex/zeroda_reflex
source /opt/zeroda-reflex/venv/bin/activate
set -a; source /opt/zeroda-reflex/.env; set +a
reflex init
reflex export --frontend-only
```

### 5. Streamlit 중지 + Reflex 시작
```bash
# Streamlit 중지
systemctl stop zeroda
systemctl disable zeroda

# Reflex 시작
systemctl start zeroda-reflex

# nginx 교체 (기존 백업 후 Reflex 설정으로 교체)
cp /etc/nginx/sites-available/zeroda /etc/nginx/sites-available/zeroda.bak.streamlit
cp /opt/zeroda-reflex/zeroda_reflex/deploy/nginx-reflex.conf /etc/nginx/sites-available/zeroda
nginx -t && systemctl restart nginx
```

### 6. 접속 확인
```
https://zeroda.co.kr
```

---

## 일상 운영

### 상태 확인
```bash
systemctl status zeroda-reflex
```

### 로그 보기
```bash
journalctl -u zeroda-reflex -n 50     # 최근 50줄
journalctl -u zeroda-reflex -f         # 실시간
```

### 코드 업데이트 (GitHub → 서버)
```bash
ssh root@223.130.131.188
bash /opt/zeroda-reflex/zeroda_reflex/deploy/update.sh
```
또는 수동으로:
```bash
cd /opt/zeroda-platform && git pull && systemctl restart zeroda-reflex
```

### DB 백업
```bash
cp /opt/zeroda-platform/zeroda.db /opt/zeroda-platform/zeroda.db.bak.$(date +%Y%m%d)
```

### 롤백 (문제 발생 시 Streamlit 복원)
```bash
systemctl stop zeroda-reflex
cp /etc/nginx/sites-available/zeroda.bak.streamlit /etc/nginx/sites-available/zeroda
systemctl start zeroda
systemctl restart nginx
```

---

## 트러블슈팅

```bash
# 포트 확인
ss -tlnp | grep -E '3000|8000'

# 프로세스 확인
ps aux | grep reflex

# nginx 오류
tail -20 /var/log/nginx/zeroda-error.log

# DB 권한
ls -la /opt/zeroda-platform/zeroda.db
```

---

## 아키텍처

```
인터넷
  │
  ▼
[nginx :443 SSL] zeroda.co.kr
  │
  ├── /_next/static/ → 정적 파일 (캐시 30일)
  ├── /_event        → WebSocket (:8000)
  ├── /api/          → 백엔드 API (:8000)
  └── /              → 프론트엔드 (:3000)
                          │
                          ▼
                     [zeroda.db]
```
