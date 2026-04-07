# zeroda 플랫폼 — 코워크(Cowork) 작업 지침
> Reflex 전환 완료 | 2026-04-06 | 작업 시작 전 반드시 이 파일을 먼저 읽으세요

---

## 1. 프로젝트 기본 정보

| 항목 | 내용 |
|---|---|
| 플랫폼명 | zeroda (제로다 폐기물데이터플랫폼) |
| GitHub 저장소 | github.com/rmfams08-code/zeroda-platform |
| 배포 URL (구) | ~~zeroda2026.streamlit.app~~ (폐기) |
| **배포 URL** | **https://zeroda.co.kr** (네이버클라우드 Reflex) |
| 로컬 작업 폴더 | C:\Users\admin\Desktop\신규제로다코워크전용\zeroda_platform |
| **개발 프레임워크** | **Reflex** (Streamlit 전환 완료, 2026-04-06) |
| 개발 도구 | Claude Chat + Cowork |
| **메인 코드 폴더** | **zeroda_reflex/** |
| Streamlit 코드 | 루트 (main.py 등) — 레거시, 수정 불필요 |

---

## 2. 파일 구조 (경로 규칙)

### 2-1. Reflex 앱 (메인 — zeroda_reflex/)

```
zeroda_reflex/
├── rxconfig.py                        ← Reflex 설정 (포트 3000/8000, DB경로)
├── requirements.txt                   ← reflex, bcrypt, openpyxl, anthropic
├── deploy/                            ← 서버 배포 파일
│   ├── DEPLOY_GUIDE.md               ← 배포 가이드 (zeroda.co.kr 직결)
│   ├── setup.sh                      ← 자동 설치 스크립트
│   ├── update.sh                     ← 코드 업데이트 스크립트
│   ├── zeroda-reflex.service         ← systemd 서비스
│   ├── nginx-reflex.conf             ← nginx 설정 (SSL+WebSocket)
│   └── .env.example                  ← 환경변수 템플릿
└── zeroda_reflex/
    ├── zeroda_reflex.py               ← 메인 엔트리 (라우팅, 5개 역할)
    ├── state/
    │   ├── auth_state.py              ← 인증 상태 (로그인/로그아웃)
    │   ├── driver_state.py            ← 기사 상태 (안전점검+수거+퇴근+날씨)
    │   ├── vendor_state.py            ← 업체관리자 상태 (7메뉴+SMS)
    │   ├── admin_state.py             ← 본사관리자 상태 (9메뉴+SMS+차트)
    │   ├── school_state.py            ← 학교 상태 (5탭)
    │   ├── edu_state.py               ← 교육청 상태 (6탭)
    │   └── meal_state.py              ← 급식담당자 상태 (6메뉴+AI)
    ├── pages/
    │   ├── login.py                   ← 로그인 페이지
    │   ├── driver.py                  ← 기사 대시보드 (날씨+진행률+삭제)
    │   ├── vendor_admin.py            ← 업체관리자 (7탭+차트+SMS)
    │   ├── hq_admin.py                ← 본사관리자 (9탭+차트+SMS)
    │   ├── school.py                  ← 학교 (5탭)
    │   ├── edu_office.py              ← 교육청 (6탭)
    │   └── meal_manager.py            ← 급식담당자 (6탭+차트)
    └── utils/
        ├── database.py                ← DB 유틸 (기존 zeroda.db 공유)
        ├── weather_service.py         ← 기상청 API (ASOS+초단기실황)
        └── sms_service.py             ← SOLAPI SMS 발송
```

### 2-2. Streamlit 코드 (레거시 — 루트)

```
zeroda-platform/
├── main.py                        ← (레거시) Streamlit 메인 라우터
├── database/                      ← (레거시) DB 관련
├── config/                        ← (레거시) 설정
├── services/                      ← (레거시) 외부 서비스
└── modules/                       ← (레거시) 역할별 화면
```

> ⚠️ Streamlit 코드는 레거시입니다. Reflex 전환 완료 후 수정 불필요.
> 롤백이 필요한 경우에만 사용합니다.

---

## 3. 핵심 개발 원칙 (절대 준수)

| 원칙 | 내용 |
|---|---|
| ✅ 작업 후 문법 검증 | ast.parse로 Python 문법 오류 확인 |
| ✅ 함수명/파일명 변경 금지 | 다른 파일에서 참조 중 |
| ✅ DB 스키마 변경 금지 | zeroda.db 테이블 구조 그대로 유지 |
| ✅ 새 작업은 zeroda_reflex/ 에서 | Reflex 코드만 수정 |
| ✅ Streamlit 코드 수정 금지 | 레거시 — 롤백용으로만 보존 |
| ✅ 환경변수로 API 키 관리 | os.environ 사용 (Streamlit secrets 사용 안함) |

---

## 4. 주요 DB 테이블 & 컬럼

| 테이블 | 핵심 컬럼 | 비고 |
|---|---|---|
| `users` | role, vendor, schools, edu_office | 역할별 접근 제어 |
| `school_master` | school_name, alias | 별칭 매칭용 |
| `customer_info` | price_food, price_recycle, price_general | 품목별 단가 3종 |
| `real_collection` | school_name, collect_date, item_type, weight | ⚠️ 한글/영문 컬럼 혼재 |
| `schedules` | vendor, month(YYYY-MM 또는 YYYY-MM-DD) | 월별+일별 구분 |
| `school_zone_violations` | vendor, driver, violation_date, fine_amount | 수정3 신규 |
| `safety_scores` | vendor, year_month, total_score, grade | 수정3 신규 |

---

## 5. 작업 이력

### Streamlit 시대 (수정1~5, 레거시)

| 버전 | 주요 내용 |
|---|---|
| 수정1 | 중복 제거, 이메일 key 변수화, 거래처 단가 UI, 학교 별칭 매칭 구조 개선 |
| 수정2 | ESG 보고서 PDF, school/dashboard 신규, edu_office 탭 추가 |
| 수정3 | 교육청 관할학교 연동 수정, 수거일정 일별 등록, 안전관리 평가 |
| 수정4 | 보안강화(bcrypt), 자가회원가입+관리자승인, 네이버클라우드 배포 |
| 수정5 | 안전점검 일1회, PWA, 자동로그인, 전역 세션유지 |

### ✅ Reflex 전환 완료 (Phase 0~10)

| Phase | 내용 | 상태 |
|---|---|---|
| 0 | 프로젝트 구조 + rxconfig + database.py | ✅ |
| 1 | 인증(auth_state) + 로그인 페이지 | ✅ |
| 2 | 기사모드 (안전점검+수거입력+퇴근) | ✅ |
| 3 | 업체관리자 (7메뉴) | ✅ |
| 4 | 본사관리자 (9메뉴) | ✅ |
| 5 | 학교 (5탭) + 교육청 (6탭) | ✅ |
| 6 | 급식담당자 (6메뉴+AI잔반분석) | ✅ |
| 7 | 기사 수거 삭제 + 진행률 표시 + 미완료 학교 배지 | ✅ |
| 8 | 날씨 API + SMS 발송 + 외부서비스 연동 | ✅ |
| 9 | recharts 차트 (관리자+급식담당자) | ✅ |
| 10 | 서버 배포 파일 (nginx+systemd+setup.sh) | ✅ |

### ⏳ 서버 배포 (미실행)

> 코드는 모두 완성. 서버에서 setup.sh 실행만 남음.
> 배포 절차: `zeroda_reflex/deploy/DEPLOY_GUIDE.md` 참고

---

## 6. 서버 배포 & 운영

### 6-1. 서버 정보
| 항목 | 내용 |
|---|---|
| 서버명 | zeroda-web (네이버클라우드 KVM) |
| 공인 IP | 223.130.131.188 |
| 접속 계정 | root |
| 도메인 | zeroda.co.kr |
| **Reflex 경로** | /opt/zeroda-reflex |
| **서비스명** | zeroda-reflex (systemd) |
| 프론트 포트 | 3000 |
| 백엔드 포트 | 8000 |
| DB | /opt/zeroda-platform/zeroda.db |
| 인증서 | Let's Encrypt (자동갱신) |

### 6-2. 최초 배포 (한 번만)
```bash
ssh root@223.130.131.188
cd /opt/zeroda-platform && git pull
bash zeroda_reflex/deploy/setup.sh
# → 이후 DEPLOY_GUIDE.md 4~6단계 수행
```

### 6-3. 코드 업데이트 (수정 시마다)
```bash
ssh root@223.130.131.188
bash /opt/zeroda-reflex/zeroda_reflex/deploy/update.sh
```
또는 수동:
```bash
cd /opt/zeroda-platform && git pull && systemctl restart zeroda-reflex
```

### 6-4. 주요 운영 명령어
```bash
# 상태 확인
systemctl status zeroda-reflex

# 로그 보기
journalctl -u zeroda-reflex -n 50
journalctl -u zeroda-reflex -f          # 실시간

# 재시작
systemctl restart zeroda-reflex

# nginx
nginx -t && systemctl restart nginx

# 포트 확인
ss -tlnp | grep -E '3000|8000'
```

### 6-5. 롤백 (문제 발생 시 Streamlit 복원)
```bash
systemctl stop zeroda-reflex
cp /etc/nginx/sites-available/zeroda.bak.streamlit /etc/nginx/sites-available/zeroda
systemctl start zeroda
systemctl restart nginx
```

### 6-6. GitHub 업로드
```
1. 로컬에서 파일 수정
2. GitHub → 해당 폴더 이동 → 파일 편집 → Commit
3. 서버에서 update.sh 실행
```

---

## 7. 절대 하지 말아야 할 것

| ❌ 금지 | 이유 |
|---|---|
| Streamlit 코드(루트) 수정 | 레거시 — 롤백용으로만 보존 |
| DB 스키마(테이블/컬럼) 변경 | zeroda.db 기존 구조 유지 필수 |
| 기존 함수 삭제·이름 변경 | 다른 파일에서 참조 중 |
| .env 파일을 GitHub에 업로드 | API 키 노출 위험 |
| 한 번에 너무 많은 작업 요청 | 오류 추적 어려움, 하나씩 진행 |

---

## 8. 외부 서비스 API

| 서비스 | 용도 | 환경변수 |
|---|---|---|
| 기상청 ASOS | 일별 기상데이터 | KMA_API_KEY |
| 기상청 초단기실황 | 실시간 날씨 알림 | KMA_API_KEY |
| SOLAPI (CoolSMS) | 거래명세서 SMS 발송 | COOLSMS_API_KEY, COOLSMS_API_SECRET, COOLSMS_SENDER |
| 네이버웍스 SMTP | 이메일 발송 | NAVER_SMTP_USER, NAVER_SMTP_PASS |
| Anthropic | AI 잔반분석 | ANTHROPIC_API_KEY |

> 2026-04-07 webhook 정상화 재검증 완료
