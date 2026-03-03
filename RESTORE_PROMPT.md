# ZERODA 플랫폼 누락 기능 복원 프롬프트

## 프로젝트 컨텍스트

- **플랫폼명**: ZERODA (제로다 폐기물데이터플랫폼)
- **운영사**: 하영자원 (경기도 화성시)
- **기술스택**: Python, Streamlit, SQLite
- **배포**: zeroda2026.streamlit.app
- **GitHub**: RMFAMS08-code/zeroda-platform

### 현재 폴더 구조
```
zeroda-platform/
├── main.py
├── requirements.txt
├── config/
│   ├── settings.py
│   └── __init__.py
├── database/
│   ├── db_init.py
│   └── db_manager.py
├── auth/
│   ├── login.py
│   └── account_manager.py
├── services/
│   ├── pdf_generator.py
│   ├── excel_generator.py
│   └── email_service.py
└── modules/
    ├── hq_admin/
    │   ├── dashboard.py
    │   ├── data_tab.py
    │   ├── settlement_tab.py
    │   ├── schedule_tab.py
    │   ├── vendor_mgmt_tab.py
    │   └── account_mgmt_tab.py
    ├── vendor_admin/
    │   ├── dashboard.py
    │   ├── collection_tab.py
    │   ├── schedule_tab.py
    │   ├── customer_tab.py
    │   ├── biz_tab.py
    │   └── statement_tab.py
    ├── driver/
    │   ├── dashboard.py
    │   └── collection_input.py
    ├── school/
    │   └── dashboard.py
    └── edu_office/
        └── dashboard.py
```

---

## 복원 작업 1: CSV/엑셀 데이터 업로드

### 대상 파일
`modules/hq_admin/data_tab.py` 수정  
`services/upload_handler.py` 신규 생성

### 요구사항
- CSV, XLSX 파일 업로드 지원
- 업로드 후 상위 10행 미리보기 표시
- DB 컬럼 자동 매핑 (CSV 컬럼명 ↔ DB 컬럼명)
  - 예: `날짜` → `collect_date`, `학교명` → `school_name`, `음식물(kg)` → `weight`
- 중복 데이터 처리 옵션 (덮어쓰기 / 건너뛰기)
- 저장 테이블 선택: `real_collection` 또는 `sim_collection`
- 업로드 결과 요약 표시 (성공 N건 / 실패 N건)
- 한글 컬럼명 완벽 지원

### 참고 CSV 컬럼 구조 (hayoung_real_2024_fixed.csv)
```
날짜, 학교명, 음식물(kg), 단가(원), 공급가, 재활용방법, 재활용업체, 월, 년도, 월별파일
```

### DB 매핑 테이블
| CSV 컬럼 | DB 컬럼 |
|---------|--------|
| 날짜 | collect_date |
| 학교명 | school_name |
| 음식물(kg) | weight |
| 단가(원) | unit_price |
| 공급가 | amount |
| 재활용방법 | item_type |
| 재활용업체 | vendor |

---

## 복원 작업 2: 안전관리 모듈

### 대상 파일 (신규 생성)
```
modules/hq_admin/safety_tab.py
modules/vendor_admin/safety_tab.py
```

### DB 테이블 추가 (db_init.py 수정)
```sql
-- 안전교육 이력
CREATE TABLE IF NOT EXISTS safety_education (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT,
    driver TEXT,
    edu_date TEXT,
    edu_type TEXT,        -- 정기교육, 신규교육, 특별교육
    edu_hours INTEGER,
    instructor TEXT,
    result TEXT,          -- 이수, 미이수
    memo TEXT,
    created_at TEXT
);

-- 안전점검 체크리스트
CREATE TABLE IF NOT EXISTS safety_checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT,
    driver TEXT,
    check_date TEXT,
    vehicle_no TEXT,
    check_items TEXT,     -- JSON: {항목: 결과}
    total_ok INTEGER,
    total_fail INTEGER,
    inspector TEXT,
    memo TEXT,
    created_at TEXT
);

-- 사고 신고
CREATE TABLE IF NOT EXISTS accident_report (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor TEXT,
    driver TEXT,
    occur_date TEXT,
    occur_location TEXT,
    accident_type TEXT,   -- 교통사고, 작업중사고, 차량고장, 기타
    severity TEXT,        -- 경상, 중상, 사망, 재산피해
    description TEXT,
    action_taken TEXT,
    status TEXT,          -- 신고완료, 처리중, 완료
    created_at TEXT
);
```

### 기능 요구사항

**본사 관리자 (hq_admin/safety_tab.py)**
- 전체 업체 안전교육 현황 조회
- 안전점검 결과 조회
- 사고 신고 접수 및 처리 현황

**외주업체 관리자 (vendor_admin/safety_tab.py)**
- 소속 기사 안전교육 입력/조회
- 차량 안전점검 체크리스트 입력
  - 점검 항목: 브레이크, 타이어, 등화장치, 와이퍼, 냉각수, 엔진오일, 안전벨트, 소화기
- 사고 신고 입력

### main.py 메뉴 추가
```python
# hq_admin 메뉴에 추가
("안전관리", "safety"),

# vendor_admin 메뉴에 추가  
("안전관리", "safety"),
```

---

## 복원 작업 3: 탄소배출감축량 모듈

### 대상 파일 (신규 생성)
```
modules/hq_admin/carbon_tab.py
modules/edu_office/carbon_tab.py
services/carbon_calculator.py
```

### DB 테이블 추가 (db_init.py 수정)
```sql
CREATE TABLE IF NOT EXISTS carbon_reduction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_name TEXT,
    vendor TEXT,
    year INTEGER,
    month INTEGER,
    food_waste_kg REAL DEFAULT 0,    -- 음식물 수거량
    recycle_kg REAL DEFAULT 0,        -- 재활용 수거량
    general_kg REAL DEFAULT 0,        -- 일반 수거량
    carbon_reduced REAL DEFAULT 0,    -- 탄소감축량 (kg CO2)
    tree_equivalent REAL DEFAULT 0,   -- 나무 식재 환산 (그루)
    created_at TEXT
);
```

### 탄소감축 계산 공식 (services/carbon_calculator.py)
```python
# 환경부 기준 탄소배출계수
CARBON_FACTOR = {
    '음식물': 0.271,   # kg CO2 / kg (매립 대비 감축)
    '재활용': 0.461,   # kg CO2 / kg
    '일반':   0.054,   # kg CO2 / kg
}
TREE_ABSORPTION = 6.6  # kg CO2 / 그루 / 년

def calculate_carbon_reduction(food_kg, recycle_kg, general_kg):
    total = (food_kg * CARBON_FACTOR['음식물']
           + recycle_kg * CARBON_FACTOR['재활용']
           + general_kg * CARBON_FACTOR['일반'])
    trees = total / TREE_ABSORPTION
    return round(total, 2), round(trees, 1)
```

### 기능 요구사항

**본사 관리자 (hq_admin/carbon_tab.py)**
- 연도/월별 전체 탄소감축량 집계
- 학교별 탄소감축 순위
- 월별 추이 차트 (st.line_chart)
- 교육청 제출용 리포트 PDF/엑셀 다운로드

**교육청 (edu_office/carbon_tab.py 또는 dashboard.py에 탭 추가)**
- 관할 학교 전체 탄소감축 현황
- 학교별 비교 차트
- 연간 성과 요약

### main.py 메뉴 추가
```python
# hq_admin 메뉴에 추가
("탄소감축 현황", "carbon"),

# edu_office 메뉴에 추가
("탄소감축 현황", "carbon"),
```

---

## 복원 작업 4: 디자인 모듈화

### 대상 파일 (신규 생성)
```
config/styles.py      -- 공통 CSS
config/components.py  -- 재사용 UI 컴포넌트
```

### config/styles.py 구조
```python
# 공통 CSS - 모든 페이지에 적용
COMMON_CSS = """..."""

# 역할별 사이드바 색상
ROLE_COLORS = {
    'admin':        '#1a73e8',
    'vendor_admin': '#34a853',
    'driver':       '#fbbc04',
    'school_admin': '#ea4335',
    'edu_office':   '#9c27b0',
}
```

### config/components.py 구조
```python
def metric_card(title, value, subtitle=None, color='#1a73e8'):
    """통일된 메트릭 카드"""

def status_badge(status):
    """수거 상태 배지 - draft/submitted/confirmed/rejected"""

def section_header(title, icon=''):
    """섹션 헤더"""

def empty_state(message, icon='📭'):
    """데이터 없음 상태"""

def data_table(df, key=None):
    """스타일 적용된 데이터프레임"""
```

### 적용 방법
기존 각 모듈에서:
```python
# 기존
st.metric("총 수거량", f"{total:,.1f} kg")

# 변경 후
from config.components import metric_card
metric_card("총 수거량", f"{total:,.1f} kg", color='#34a853')
```

---

## 작업 순서 권장

```
1단계: 데이터 업로드 (즉시 사용 필요)
  → services/upload_handler.py
  → modules/hq_admin/data_tab.py 수정

2단계: 탄소감축량 (교육청 제출 필요)
  → services/carbon_calculator.py
  → modules/hq_admin/carbon_tab.py
  → modules/edu_office/ 탭 추가

3단계: 안전관리
  → modules/hq_admin/safety_tab.py
  → modules/vendor_admin/safety_tab.py

4단계: 디자인 모듈화 (마지막)
  → config/styles.py
  → config/components.py
  → 전체 모듈 일괄 적용
```

---

## 주의사항

1. **SQLite DB 초기화**: `db_init.py` 수정 후 반드시 Streamlit Reboot 필요
2. **한글 깨짐 방지**: PDF는 `HYSMyeongJo-Medium` CJK 폰트, 이메일은 `Header(subject, 'utf-8')` 사용
3. **Streamlit Cloud 제약**: 재시작 시 SQLite 데이터 초기화됨 (추후 영구 스토리지 검토 필요)
4. **토큰 절약**: 각 작업은 섹션별로 분리해서 요청할 것

---

