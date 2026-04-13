# zeroda 플랫폼 — 알림(Notification) 정책
> UI Phase 5 산출물 | 2026-04-13 | 신규 코드 작성 시 반드시 준수

---

## 1. 알림 유형 분류

| 유형 | 용도 | 컴포넌트 | 표시 위치 |
|---|---|---|---|
| **토스트 (Toast)** | CRUD 결과, 발송 결과, 삭제 확인 등 **일회성 액션 피드백** | `notify_success/error/warning/info` (shared.py) | 화면 우상단, 자동 사라짐 |
| **인라인 콜아웃 (Callout)** | 폼 유효성 결과, 저장 상태 등 **컨텍스트 유지가 필요한 피드백** | `rx.callout` + `_msg` State 변수 | 폼 내부, 해당 섹션 안 |

---

## 2. 언제 어떤 알림을 쓸 것인가

### 토스트 (Toast) 사용 — 아래 상황에서 사용

- 데이터 저장/수정/삭제 완료 또는 실패
- SMS/이메일 발송 완료 또는 실패
- 파일 업로드/다운로드 완료
- 로그인/로그아웃 결과
- 일괄 처리(일괄승인, 일괄삭제) 완료
- 외부 API 호출 결과 (날씨, NEIS 등)

### 인라인 콜아웃 (Callout) 사용 — 아래 상황에서 사용

- 폼 입력값 유효성 검사 결과 (사용자가 수정해야 하므로 보여야 함)
- 설정/프로필 저장 후 결과 표시 (해당 폼 바로 아래)
- 안전점검 결과 요약 (기사 페이지)
- 복잡한 작업의 중간 상태 안내

### 판단 기준 요약

> **"사용자가 다른 탭으로 이동해도 괜찮은 피드백"** → 토스트  
> **"사용자가 해당 위치에서 추가 액션을 해야 하는 피드백"** → 인라인 콜아웃

---

## 3. 토스트 헬퍼 함수 (shared.py)

```python
from zeroda_reflex.components.shared import (
    notify_success, notify_error, notify_warning, notify_info
)

# State 메서드에서 사용
yield notify_success("저장 완료")
yield notify_error("저장 실패: 서버 오류")
yield notify_warning("입력값을 확인하세요")
yield notify_info("업로드 완료. 추출된 태그 3개")
```

### 기본 설정값 (TOAST_DEFAULTS)

| 레벨 | duration | 용도 |
|---|---|---|
| success | 3초 | 성공 알림 (빨리 사라져도 OK) |
| error | 5초 | 에러 (사용자가 읽을 시간 필요) |
| warning | 4초 | 경고 (중간 수준) |
| info | 3초 | 안내 (성공과 동일) |

> duration, position 등 일괄 변경은 `TOAST_DEFAULTS`에서 한 곳만 수정

---

## 4. 기존 코드 현황 (2026-04-13 기준)

### 토스트 사용 중 (유지)
| 파일 | 건수 | 비고 |
|---|---|---|
| admin_state.py | 12 | 문서서비스 + 일정 |
| driver_state.py | 18 | 수거/GPS/음성 |
| document_state.py | 15 | 계약서/견적서 |
| vendor_document_state.py | 16 | 업체용 문서서비스 |

### 인라인 콜아웃 사용 중 (유지)
| 파일 | 건수 | 비고 |
|---|---|---|
| vendor_admin.py | 9 | 폼 저장 결과 |
| hq_admin.py | 9 | 폼/계정 관리 |
| meal_manager.py | 6 | 급식/승인 |
| driver.py | 3 | 안전점검 결과 |
| school.py | 1 | 급식 |
| edu_office.py | 2 | 교육청 |

### 변환 대상 (상용화 2단계에서 진행)
| 대상 | 현재 | 변환 후 | 우선순위 |
|---|---|---|---|
| vendor_state 주요 액션 | _msg 변수만 | _msg 유지 + toast 추가 | P2 |
| meal_state 주요 액션 | _msg 변수만 | _msg 유지 + toast 추가 | P2 |
| school_state 주요 액션 | _msg 변수만 | _msg 유지 + toast 추가 | P3 |

> 기존 인라인 콜아웃은 제거하지 않고, toast를 **추가**하는 방식으로 통일  
> (인라인: 폼 컨텍스트 유지, 토스트: 액션 완료 확인)

---

## 5. 신규 코드 작성 규칙

1. **State 메서드에서 CRUD 결과 알림** → 반드시 `notify_*` 헬퍼 사용
2. **직접 `rx.toast.success(...)` 호출 금지** → 헬퍼를 통해야 duration 등 일괄 관리 가능
3. **인라인 콜아웃이 필요한 경우** → 기존 패턴 유지 (`rx.cond` + `_msg` + `rx.callout`)
4. **둘 다 필요한 경우** → 토스트 + 인라인 콜아웃 병용 가능 (예: 폼 저장 → 토스트로 "저장 완료" + 콜아웃으로 상세 결과)

---

## 6. 점진적 마이그레이션 계획

| 단계 | 작업 | 시기 |
|---|---|---|
| **Phase 5-1** (현재) | 헬퍼 함수 추가, 정책 문서 작성 | 2026-04-13 |
| **Phase 5-2** | 신규 코드에 헬퍼 적용 (문서서비스 등) | 상용화 1단계 |
| **Phase 5-3** | vendor_state/meal_state에 toast 추가 | 상용화 2단계 |
| **Phase 5-4** | 전체 일괄 점검 + `rx.toast` 직접호출 → 헬퍼 전환 | 상용화 3단계 |
