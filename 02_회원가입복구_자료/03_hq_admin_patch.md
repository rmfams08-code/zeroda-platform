# hq_admin.py 부분 수정 패치

> 파일: `zeroda_reflex/zeroda_reflex/pages/hq_admin.py`
> 수정 2곳, 모두 단순 리스트 항목 추가입니다. 이름/구조 변경 없음.

---

## 패치 #1 — ROLE_LABELS 에 meal_manager 추가 (줄 21~27)

### 수정 전
```python
ROLE_LABELS = {
    "admin": "본사관리자",
    "vendor_admin": "업체관리자",
    "driver": "기사",
    "school": "학교",
    "edu_office": "교육청",
}
```

### 수정 후
```python
ROLE_LABELS = {
    "admin": "본사관리자",
    "vendor_admin": "업체관리자",
    "driver": "기사",
    "school": "학교",
    "meal_manager": "급식담당자",
    "edu_office": "교육청",
}
```

이유: 가입 시 meal_manager 역할이 들어오지만 ROLE_LABELS에 없어서 사용자 목록 테이블의 역할 배지가 영문 "meal_manager"로 그대로 노출됨.

---

## 패치 #2 — 계정관리 역할 필터에 meal_manager 추가 (줄 358)

### 수정 전
```python
            rx.select(
                ["전체", "admin", "vendor_admin", "driver", "school", "edu_office"],
                value=AdminState.acct_filter_role,
```

### 수정 후
```python
            rx.select(
                ["전체", "admin", "vendor_admin", "driver", "school", "meal_manager", "edu_office"],
                value=AdminState.acct_filter_role,
```

이유: 필터 옵션에 meal_manager가 누락되어 있어, meal_manager 사용자만 필터링해서 볼 수 없음.

---

## 검증 방법
```bash
cd /opt/zeroda-platform
python3 -c "import ast; ast.parse(open('zeroda_reflex/zeroda_reflex/pages/hq_admin.py').read()); print('OK')"
grep -n "meal_manager" zeroda_reflex/zeroda_reflex/pages/hq_admin.py | head -5
```
출력에 ROLE_LABELS와 select 두 곳에서 meal_manager가 보여야 합니다.

---

## ⚠️ 주의 — 사례5 회피
- 이 패치는 **두 줄 추가만** 합니다. 함수명/구조 변경 없음.
- 다른 함수(`_role_badge`의 color_map 등)는 수정하지 않습니다 (`get(role, role)` 폴백으로 동작).
- Reflex Var + 결합 변경 없음 (단순 리스트 항목 추가).
