# zeroda_reflex/utils/colors.py
# 전역 색상 상수 — vendor_admin.py, hq_admin.py 등에서 공통 사용
# 수정 시 이 파일만 바꾸면 전체 페이지에 반영됨

# ── 브랜드 색상 (zeroda 메인 그린) ──────────────────────
PRIMARY           = "#38bd94"
PRIMARY_ALPHA_08  = "rgba(56,189,148,0.08)"
PRIMARY_ALPHA_10  = "rgba(56,189,148,0.10)"
PRIMARY_ALPHA_12  = "rgba(56,189,148,0.12)"
PRIMARY_ALPHA_30  = "rgba(56,189,148,0.3)"

# ── Slate 팔레트 (텍스트 / 배경 / 테두리) ───────────────
TEXT_900         = "#0f172a"   # 가장 진한 텍스트
TEXT_800         = "#1e293b"   # 기본 텍스트
TEXT_700         = "#334155"   # 약간 연한 텍스트
TEXT_GRAY        = "#374151"   # 회색빛 텍스트
TEXT_600         = "#475569"   # 뮤트 텍스트
TEXT_500         = "#64748b"   # 서브 텍스트 (가장 많이 사용)
TEXT_400         = "#94a3b8"   # 플레이스홀더 / 보조
TEXT_300         = "#cbd5e1"   # 비활성화 텍스트
TEXT_GRAY_400    = "#9ca3af"   # gray-400

BG_WHITE         = "#ffffff"
BG_50            = "#f8fafc"   # 호버 배경
BG_100           = "#f1f5f9"   # 구분선 배경
BORDER           = "#e2e8f0"   # 기본 테두리

# ── 상태 색상 ────────────────────────────────────────────
SUCCESS          = "#22c55e"
SUCCESS_DARK     = "#16a34a"
SUCCESS_BG       = "#f0fdf4"

ERROR            = "#ef4444"
ERROR_DARK       = "#dc2626"
ERROR_BG         = "#fef2f2"
ERROR_ALPHA_08   = "rgba(239,68,68,0.08)"
ERROR_ALPHA_10   = "rgba(239,68,68,0.10)"
ERROR_ALPHA_30   = "rgba(239,68,68,0.3)"

# ── 보조 색상 ────────────────────────────────────────────
BLUE             = "#3b82f6"
BLUE_ALPHA_10    = "rgba(59,130,246,0.10)"
BLUE_BG          = "#eff6ff"
BLUE_BORDER      = "#bfdbfe"

AMBER            = "#f59e0b"
AMBER_ALPHA_10   = "rgba(245,158,11,0.10)"
AMBER_BG         = "#fef3c7"
AMBER_BG_LIGHT   = "#fffbeb"
AMBER_DARK       = "#b45309"
AMBER_DARKER     = "#92400e"

PURPLE           = "#8b5cf6"
PURPLE_ALPHA_10  = "rgba(139,92,246,0.10)"

# ── 그림자 ───────────────────────────────────────────────
SHADOW_SM        = "rgba(0,0,0,0.04)"
SHADOW_MD        = "rgba(0,0,0,0.05)"
