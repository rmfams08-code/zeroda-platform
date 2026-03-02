# zeroda_platform/database/db_init.py

def init_db():
    """Supabase 사용 시 테이블은 대시보드에서 생성 — 여기선 패스"""
    pass

def migrate_csv_to_db(*args, **kwargs):
    """초기 데이터 마이그레이션은 Supabase 대시보드에서 직접 수행"""
    pass
```

---

## 4단계 : 깃허브 + Streamlit Cloud 배포

### A. 필수 파일 2개 생성

**① `requirements.txt`** (zeroda_platform 폴더 루트)
```
streamlit>=1.32.0
supabase>=2.3.0
pandas>=2.0.0
openpyxl>=3.1.0
reportlab>=4.0.0
```

**② `.gitignore`** (깃허브에 올리면 안 되는 파일 차단)
```
# DB 파일 절대 업로드 금지
*.db
*.sqlite
*.sqlite3

# 비밀 설정
.env
secrets.toml
.streamlit/secrets.toml

# 파이썬
__pycache__/
*.pyc
.DS_Store
```

### B. 깃허브 업로드
```
GitHub 새 레포 생성
  이름: zeroda-platform
  Private (비공개) ← 반드시 Private
  
zeroda_platform 폴더 전체 업로드
```

### C. Streamlit Cloud 배포

**① https://share.streamlit.io 접속**

**② New app 클릭**
```
Repository : zeroda-platform
Branch     : main
Main file  : main.py   ← zeroda_platform/main.py 경로