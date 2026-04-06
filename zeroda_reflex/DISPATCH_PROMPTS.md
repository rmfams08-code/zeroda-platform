# zeroda Reflex 전환 — Dispatch 프롬프트 모음

> 여행 중 모바일 Dispatch에서 **하나씩 순서대로** 보내세요.
> 이전 작업 완료 알림을 확인한 후 다음 프롬프트를 보내세요.
> 각 프롬프트는 독립적으로 동작하도록 설계되었습니다.

---

## 프롬프트 #1: 업체관리자 기본 구조 + 라우팅

```
zeroda Reflex 전환 작업입니다. 아래 순서대로 진행하세요.

1. 먼저 CLAUDE.md를 읽으세요:
   zeroda_platform/CLAUDE.md

2. zeroda_reflex/ 폴더의 기존 파일들을 모두 읽으세요:
   - rxconfig.py
   - zeroda_reflex/zeroda_reflex.py (메인 라우터)
   - zeroda_reflex/state/auth_state.py
   - zeroda_reflex/state/driver_state.py (참고용)
   - zeroda_reflex/utils/database.py
   - zeroda_reflex/pages/login.py
   - zeroda_reflex/pages/driver.py (참고용)

3. 업체관리자(vendor_admin) 모드의 기본 구조를 만드세요:

   (A) zeroda_reflex/state/vendor_state.py 생성:
   - AuthState를 상속하는 VendorState 클래스
   - 공통 상태: selected_year, selected_month (연/월 필터)
   - active_tab: str (현재 활성 탭 이름)
   - 탭 전환 이벤트 핸들러: set_active_tab(tab_name)
   - on_vendor_load 이벤트: 인증 확인 + 초기 데이터 로드

   (B) zeroda_reflex/pages/vendor_admin.py 생성:
   - 사이드바 네비게이션 (7개 메뉴):
     수거현황, 수거데이터, 거래처관리, 일정관리, 정산관리, 안전관리, 설정
   - 탭 선택에 따라 다른 콘텐츠 영역 표시 (rx.cond 사용)
   - 일단 각 탭은 "준비 중" 플레이스홀더로 표시
   - 상단 헤더: ZERODA 로고 + 업체명 + 로그아웃
   - 모바일 반응형 레이아웃 고려

   (C) zeroda_reflex/zeroda_reflex.py 수정:
   - vendor_admin 페이지 import 추가
   - app.add_page(vendor_admin_page, route="/vendor", ...) 등록
   - on_load=VendorState.on_vendor_load 설정

   (D) zeroda_reflex/state/auth_state.py 수정:
   - _redirect_by_role에서 vendor_admin → "/vendor" 리다이렉트 추가

4. 핵심 규칙:
   - 기존 Streamlit 코드(zeroda_platform/)는 절대 수정 금지
   - zeroda_reflex/ 폴더에서만 작업
   - 기존 DB 스키마 변경 금지
   - Reflex 0.8.x API 사용 (아이콘은 lucide 이름: circle_check, triangle_alert 등)
   - rx.radio_group은 리스트 방식: rx.radio_group(["A","B","C"], ...)
   - rx.progress의 value는 int 타입
   - 작업 후 반드시 ast.parse로 모든 수정 파일 문법 검증
```

---

## 프롬프트 #2: 수거현황 대시보드

```
zeroda Reflex 전환 — 업체관리자 수거현황 대시보드 구현

1. 먼저 읽을 파일:
   - zeroda_platform/CLAUDE.md
   - zeroda_reflex/zeroda_reflex.py
   - zeroda_reflex/state/vendor_state.py
   - zeroda_reflex/pages/vendor_admin.py
   - zeroda_reflex/utils/database.py
   - (참고) zeroda_platform/modules/vendor_admin/dashboard.py (기존 Streamlit)

2. database.py에 필요한 함수 추가:
   - get_monthly_collections(vendor, year, month): 월별 수거 데이터 조회
   - get_collection_summary_by_school(vendor, year, month): 학교별 수거량 집계
   - get_vendor_schools(vendor): 업체 배정 학교 목록

3. vendor_state.py에 대시보드 상태 추가:
   - monthly_collections: list[dict] (월별 수거 데이터)
   - school_summary: list[dict] (학교별 요약)
   - total_weight, total_count, school_count (KPI 메트릭)
   - load_dashboard_data() 이벤트 핸들러

4. vendor_admin.py의 "수거현황" 탭 구현:
   - 연/월 선택 필터
   - KPI 카드 3개: 총 수거량(kg), 수거 건수, 거래처 수
   - 학교별 수거량 요약 테이블
   - 배정 학교 목록 (카드 그리드)

5. 규칙:
   - zeroda_reflex/ 폴더에서만 작업
   - Reflex 0.8.x API, lucide 아이콘
   - ast.parse 검증 필수
```

---

## 프롬프트 #3: 수거데이터 관리

```
zeroda Reflex 전환 — 업체관리자 수거데이터 관리 구현

1. 먼저 읽을 파일:
   - zeroda_platform/CLAUDE.md
   - zeroda_reflex/ 폴더의 기존 파일들 전부 (state, pages, utils)
   - (참고) zeroda_platform/modules/vendor_admin/collection_tab.py

2. database.py에 함수 추가:
   - get_collections_filtered(vendor, year_month, school=None): 필터된 수거내역
   - upsert_collection(data): 수거 데이터 추가/수정
   - get_processing_confirms(vendor, status=None): 처리확인 데이터

3. vendor_state.py에 수거데이터 상태 추가:
   - collections_list: list[dict]
   - filter_school, filter_month
   - 수거 입력 폼 상태: form_school, form_date, form_item_type, form_weight, form_driver
   - save_collection() 이벤트
   - load_collections() 이벤트

4. vendor_admin.py의 "수거데이터" 탭 구현:
   - 서브탭 3개: 수거내역 조회 / 수거입력 / 처리확인
   - 수거내역: 월/학교 필터 + 데이터 테이블
   - 수거입력: 폼 (거래처, 날짜, 품목, 수거량, 기사, 메모)
   - 처리확인: 상태별 필터 + 승인/반려 버튼

5. 규칙: zeroda_reflex/만 수정, ast.parse 검증, Reflex 0.8.x API
```

---

## 프롬프트 #4: 거래처 관리

```
zeroda Reflex 전환 — 업체관리자 거래처 관리 구현

1. 먼저 읽을 파일:
   - zeroda_platform/CLAUDE.md
   - zeroda_reflex/ 폴더의 기존 파일들 전부
   - (참고) zeroda_platform/modules/vendor_admin/customer_tab.py

2. database.py에 함수 추가:
   - get_customers_by_vendor(vendor, cust_type=None): 거래처 목록 (타입 필터)
   - save_customer(data): 거래처 등록/수정
   - delete_customer(vendor, name): 거래처 삭제
   - customer_info 테이블의 컬럼: name, vendor, 사업자번호, 대표자, 주소, 업태, 종목, 이메일, 전화번호, 구분(cust_type), 재활용자, price_food, price_recycle, price_general, fixed_monthly_fee, neis_edu_code, neis_school_code

3. vendor_state.py에 거래처 상태 추가:
   - customers_list, filter_cust_type
   - 거래처 폼 상태 (등록/수정용)
   - edit_mode: bool (등록/수정 모드 전환)
   - selected_customer: str
   - save_customer(), delete_customer() 이벤트

4. vendor_admin.py의 "거래처관리" 탭 구현:
   - 서브탭 2개: 거래처 목록 / 거래처 등록·수정
   - 목록: 타입 필터 + 테이블 + 단가 설정
   - 등록·수정: 모드 전환 라디오 + 전체 필드 폼
   - 거래처 구분: 학교, 법인, 관공서, 일반, 기타, 기타2(부가세포함)
   - "기타" 타입은 월정액(fixed_monthly_fee) 사용

5. 규칙: zeroda_reflex/만 수정, ast.parse 검증, Reflex 0.8.x API
```

---

## 프롬프트 #5: 수거일정 관리

```
zeroda Reflex 전환 — 업체관리자 수거일정 관리 구현

1. 먼저 읽을 파일:
   - zeroda_platform/CLAUDE.md
   - zeroda_reflex/ 폴더의 기존 파일들 전부
   - (참고) zeroda_platform/modules/vendor_admin/schedule_tab.py

2. database.py에 함수 추가:
   - get_schedules(vendor, month=None): 일정 조회
   - save_schedule(data): 일정 등록
   - delete_schedule(schedule_id): 일정 삭제
   - get_drivers_by_vendor(vendor): 기사 목록 (users 테이블 role='driver')
   - schedules 테이블: vendor, school_name, weekdays(JSON), items(JSON), driver, month, registered_by

3. vendor_state.py에 일정 상태 추가:
   - schedules_list, schedule_filter_weekday
   - 일정 등록 폼: form_schools(다중선택), form_weekdays(다중선택), form_items(다중선택), form_driver
   - schedule_mode: "monthly" 또는 "daily" (월반복/특정일)
   - drivers_list: list[str]
   - save_schedule(), delete_schedule() 이벤트

4. vendor_admin.py의 "일정관리" 탭 구현:
   - 서브탭 2개: 일정 조회·삭제 / 일정 등록·수정
   - 조회: 요일 필터 + 품목 서브탭(음식물/재활용/일반/전체) + 일정 카드
   - 등록: 월반복/특정일 모드 선택 → 거래처·요일·품목·기사 선택 → 중복 체크 → 저장
   - NEIS 급식 연동은 복잡하므로 이 단계에서는 제외 (나중에 별도 구현)

5. 규칙: zeroda_reflex/만 수정, ast.parse 검증, Reflex 0.8.x API
```

---

## 프롬프트 #6: 정산 관리 (기본)

```
zeroda Reflex 전환 — 업체관리자 정산 관리 구현 (기본)

1. 먼저 읽을 파일:
   - zeroda_platform/CLAUDE.md
   - zeroda_reflex/ 폴더의 기존 파일들 전부
   - (참고) zeroda_platform/modules/vendor_admin/statement_tab.py

2. database.py에 함수 추가:
   - get_settlement_summary(vendor, year, month): 거래처별 정산 요약 (수거량, 금액)
   - get_expenses(vendor, year_month): 지출내역 조회
   - save_expense(data): 지출 등록
   - delete_expense(expense_id): 지출 삭제
   - get_vendor_info(vendor): 업체 정보 조회
   - 금액 계산 로직:
     · 학교/기타1: 면세 (단가 × 수거량)
     · 기타: 월정액 (fixed_monthly_fee)
     · 기타2(부가세포함): 월정액 + 10% 부가세
     · 기타 구분: 단가 × 수거량 + 10% 부가세

3. vendor_state.py에 정산 상태 추가:
   - settlement_data: list[dict] (거래처별 정산)
   - expenses_list: list[dict]
   - total_revenue, total_expense
   - 지출 입력 폼 상태
   - load_settlement(), save_expense(), delete_expense() 이벤트

4. vendor_admin.py의 "정산관리" 탭 구현:
   - 서브탭 3개: 정산현황 / 월말정산 / 지출내역
   - 정산현황: 연/월 필터 + KPI(총수거량, 공급가, 건수) + 거래처별 테이블
   - 월말정산: 거래처 타입 필터 + 수입 테이블 + 지출 테이블
   - 지출내역: 항목명/금액/지급일/메모 입력 폼 + 목록 + 삭제

   ※ PDF 거래명세서 발송, 이메일/SMS 발송은 이 단계에서 제외 (나중에 별도 구현)

5. 규칙: zeroda_reflex/만 수정, ast.parse 검증, Reflex 0.8.x API
```

---

## 프롬프트 #7: 안전관리

```
zeroda Reflex 전환 — 업체관리자 안전관리 구현

1. 먼저 읽을 파일:
   - zeroda_platform/CLAUDE.md
   - zeroda_reflex/ 폴더의 기존 파일들 전부
   - (참고) zeroda_platform/modules/vendor_admin/safety_tab.py

2. database.py에 함수 추가:
   - get_safety_education_list(vendor, year_month=None): 안전교육 기록
   - save_safety_education(data): 안전교육 등록
   - get_safety_checklist_history(vendor, year_month=None): 차량점검 기록
   - save_safety_checklist(data): 차량점검 저장
   - get_accident_reports(vendor): 사고 신고 목록
   - save_accident_report(data): 사고 신고 등록
   - get_daily_check_summary(vendor, year_month, category=None): 일일안전점검 요약

3. vendor_state.py에 안전관리 상태 추가:
   - safety_education_list, safety_checklist_list, accident_list
   - 안전교육 폼: edu_driver, edu_date, edu_type, edu_hours, edu_instructor, edu_result
   - 차량점검 8항목 체크리스트 상태
   - 사고신고 폼: acc_driver, acc_date, acc_location, acc_type, acc_severity, acc_desc
   - 일일점검 조회 상태: daily_checks_summary
   - 각각의 save/load 이벤트 핸들러

4. vendor_admin.py의 "안전관리" 탭 구현:
   - 서브탭 4개:
     · 안전교육 입력/조회: 폼 + 기록 테이블
     · 차량안전점검: 8항목 체크 + 양호/불량 + 이력
     · 사고신고: 폼(유형:교통/작업/차량고장/기타, 심각도:물적/경상/중상/사망) + 이력
     · 일일안전점검 조회: 월/카테고리 필터 + 요약(점검수/양호수/불량수/양호율) + 기사별 이행률

5. 규칙: zeroda_reflex/만 수정, ast.parse 검증, Reflex 0.8.x API
```

---

## 프롬프트 #8: 설정 + 마무리

```
zeroda Reflex 전환 — 업체관리자 설정 탭 + 전체 마무리

1. 먼저 읽을 파일:
   - zeroda_platform/CLAUDE.md
   - zeroda_reflex/ 폴더의 기존 파일들 전부
   - (참고) zeroda_platform/modules/vendor_admin/biz_tab.py

2. 설정 탭 구현:

   (A) database.py에 함수 추가:
   - get_biz_customers(vendor): 업장 목록
   - save_biz_customer(vendor, biz_name): 업장 등록
   - delete_biz_customer(vendor, biz_name): 업장 삭제
   - save_vendor_info(data): 업체 정보 저장
   - get_vendor_info(vendor): 업체 정보 조회

   (B) vendor_state.py에 설정 상태 추가:
   - biz_customers_list, new_biz_name
   - vendor_info: dict (업체 정보)
   - save/delete/load 이벤트

   (C) vendor_admin.py의 "설정" 탭 구현:
   - 서브탭 2개: 업장관리 / 업체정보
   - 업장관리: 목록 + 단건 등록 + 일괄 등록(줄바꿈 구분) + 삭제
   - 업체정보: 회사명, 대표자, 사업자번호, 주소, 연락처 등 수정 폼

3. 전체 점검:
   - 모든 서브탭이 정상 연결되어 있는지 확인
   - vendor_admin.py에서 7개 메뉴 모두 플레이스홀더가 아닌 실제 콘텐츠인지 확인
   - reflex run으로 컴파일 테스트 (가능하면)
   - ast.parse로 모든 수정 파일 문법 검증

4. 규칙: zeroda_reflex/만 수정, ast.parse 검증, Reflex 0.8.x API
```

---

## 사용 가이드

### 보내는 순서
1. 반드시 **#1 → #2 → ... → #8** 순서대로
2. 이전 작업 **완료 알림** 확인 후 다음 전송
3. 오류가 보이면 "이전 작업에서 오류가 있으면 수정해줘"라고 추가 지시

### 오류 발생 시
```
zeroda_reflex/ 폴더를 확인하고, 마지막 작업에서 발생한 오류를 수정해줘.
ast.parse로 전체 파일 문법 검증도 해줘.
```

### 전체 컴파일 테스트 (선택)
```
zeroda_reflex/ 폴더에서 reflex run으로 컴파일 테스트 해줘.
오류가 있으면 수정하고, 수정 내역을 알려줘.
REFLEX_USE_NPM=true 환경변수 설정 필요.
```
