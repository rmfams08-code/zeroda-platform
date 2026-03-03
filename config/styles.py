# config/styles.py
# 공통 CSS 및 역할별 색상 정의

ROLE_COLORS = {
    'admin':              '#1a73e8',
    'vendor_admin':       '#34a853',
    'driver':             '#fbbc04',
    'school_admin':       '#ea4335',
    'school_nutrition':   '#ea4335',
    'edu_office':         '#9c27b0',
}

COMMON_CSS = """
<style>
/* ── 카드 ── */
.custom-card { background-color: #ffffff !important; color: #202124 !important; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border-top: 5px solid #1a73e8; }
.custom-card-green  { border-top: 5px solid #34a853; }
.custom-card-orange { border-top: 5px solid #fbbc05; }
.custom-card-red    { border-top: 5px solid #ea4335; }
.custom-card-purple { border-top: 5px solid #9b59b6; }

/* ── 메트릭 ── */
.metric-title         { font-size: 14px; color: #5f6368 !important; font-weight: bold; margin-bottom: 5px; }
.metric-value-food    { font-size: 26px; font-weight: 900; color: #ea4335 !important; }
.metric-value-recycle { font-size: 26px; font-weight: 900; color: #34a853 !important; }
.metric-value-biz     { font-size: 26px; font-weight: 900; color: #9b59b6 !important; }
.metric-value-total   { font-size: 26px; font-weight: 900; color: #1a73e8 !important; }

/* ── 헤더 ── */
.mobile-app-header { background-color: #202124; color: #ffffff !important; padding: 15px; border-radius: 10px 10px 0 0; text-align: center; margin-bottom: 15px; }

/* ── 알림 박스 ── */
.safety-box { background-color: #e8f5e9; border: 1px solid #c8e6c9; padding: 15px; border-radius: 8px; color: #2e7d32; font-weight: bold; margin-bottom:15px; }
.alert-box  { background-color: #ffebee; border: 1px solid #ffcdd2; padding: 15px; border-radius: 8px; color: #c62828; margin-bottom: 15px; }

/* ── 역할 카드 (로그인 화면) ── */
.role-card         { background: #fff; border: 2px solid #e8eaed; border-radius: 16px; padding: 35px 20px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06); min-height: 280px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
.role-card .icon   { font-size: 64px; margin-bottom: 15px; }
.role-card .title  { font-size: 22px; font-weight: 800; color: #202124; margin-bottom: 8px; }
.role-card .desc   { font-size: 14px; color: #5f6368; line-height: 1.5; }
.role-card .arrow  { font-size: 24px; color: #1a73e8; margin-top: 12px; }

/* ── 상태 배지 ── */
.badge-draft     { background:#f1f3f4; color:#5f6368; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.badge-submitted { background:#e8f0fe; color:#1a73e8; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.badge-confirmed { background:#e6f4ea; color:#34a853; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
.badge-rejected  { background:#fce8e6; color:#ea4335; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }

/* ── 섹션 헤더 ── */
.section-header { border-left: 4px solid #1a73e8; padding-left: 12px; margin: 20px 0 12px 0; font-size: 18px; font-weight: 700; color: #202124; }

/* ── 푸터 ── */
.footer-info { text-align: center; padding: 20px; color: #777; font-size: 13px; margin-top: 30px; border-top: 1px solid #e8eaed; }
</style>
"""
