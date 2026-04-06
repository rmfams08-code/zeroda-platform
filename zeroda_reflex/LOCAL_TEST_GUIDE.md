# Reflex 로컬 테스트 가이드
> zeroda_reflex 앱을 사장님 PC에서 실행하는 방법

---

## 1단계: 사전 준비

```powershell
# PowerShell에서 실행
cd C:\Users\admin\Desktop\신규제로다코워크전용\zeroda_platform\zeroda_reflex

# Python 버전 확인 (3.11 이상 권장)
python --version

# 패키지 설치
pip install reflex>=0.8.0 bcrypt>=4.0.0
```

## 2단계: Reflex 초기화

```powershell
# 최초 1회만 실행
reflex init
```

> `bun` 설치 관련 질문이 나오면 "Y" 선택

## 3단계: DB 파일 확인

zeroda.db가 zeroda_reflex/ 폴더에 있어야 합니다.

```powershell
# 기존 DB 복사 (아직 없다면)
copy ..\zeroda.db .\zeroda.db
```

## 4단계: 앱 실행

```powershell
reflex run
```

> 첫 실행 시 시간이 좀 걸립니다.
> - 프론트엔드: http://localhost:3000
> - 백엔드: http://localhost:8000

## 5단계: 역할별 테스트

| 역할 | 라우트 | 테스트 항목 |
|---|---|---|
| 기사 | /driver | 안전점검 → 수거입력 → 퇴근 |
| 업체관리자 | /vendor | 7개 메뉴 탭 전환 |
| 본사관리자 | /admin | 9개 메뉴 탭 전환 |
| 학교 | /school | 5개 탭 + 월별 필터 |
| 교육청 | /edu | 6개 탭 + 학교/업체 필터 |
| 급식담당자 | /meal | 6개 메뉴 + 식단등록/분석 |

## 오류 발생 시

```powershell
# 오류 로그 확인
reflex run --loglevel debug

# 특정 파일만 문법 검증
python -c "import ast; ast.parse(open('zeroda_reflex/state/meal_state.py').read()); print('OK')"
```

## 중지

```
Ctrl + C
```
