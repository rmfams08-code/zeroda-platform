# zeroda_reflex/components/shared.py
# ══════════════════════════════════════════════════════════════
#  공통 UI 컴포넌트 모음
#  - 모든 페이지에서 반복되던 kpi_card, section_header, card_box 등을
#    한 곳으로 모아 중복을 제거합니다.
#  - 각 페이지에서 from zeroda_reflex.components.shared import ... 로 사용
# ══════════════════════════════════════════════════════════════
import reflex as rx


# ──────────────────────────────────────────
#  1. KPI 메트릭 카드 (3가지 변형)
# ──────────────────────────────────────────

def kpi_card(
    label: str,
    value,
    unit: str = "",
    icon: str = "bar_chart_3",
    color: str = "#3b82f6",
) -> rx.Component:
    """KPI 카드 — 기본형 (본사관리자 스타일)
    아이콘 + 라벨이 상단, 값 + 단위가 하단에 표시됩니다.

    Args:
        label: 카드 제목 (예: "총 수거량")
        value: 표시할 값 (문자열 또는 숫자, Reflex State var 가능)
        unit: 단위 (예: "kg", "건")
        icon: lucide 아이콘 이름 (예: "bar_chart_3")
        color: 아이콘 색상 (예: "#3b82f6")
    """
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=16, color=color),
                rx.text(label, font_size="12px", color="#64748b",
                        font_weight="600"),
                spacing="1",
            ),
            rx.hstack(
                rx.text(value, font_size="24px", font_weight="800",
                        color="#0f172a"),
                rx.text(unit, font_size="13px", color="#94a3b8",
                        align_self="flex-end", padding_bottom="3px"),
                spacing="1", align="end",
            ),
            spacing="1",
        ),
        bg="white",
        border_radius="12px",
        padding="16px",
        border="1px solid #e2e8f0",
        box_shadow="0 1px 4px rgba(0,0,0,0.04)",
        flex="1",
        min_width="140px",
    )


def kpi_card_compact(
    label: str,
    value,
    unit: str = "",
    icon: str = "bar_chart_3",
    color: str = "#3b82f6",
) -> rx.Component:
    """KPI 카드 — 컴팩트형 (학교/교육청/급식 스타일)
    기본형과 레이아웃은 같지만, 값 폰트 22px · border 없이 shadow만 사용합니다.

    Args:
        label: 카드 제목
        value: 표시할 값
        unit: 단위
        icon: lucide 아이콘 이름
        color: 아이콘 & 값 색상
    """
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(icon, size=16, color=color),
                rx.text(label, font_size="12px", color="#64748b"),
                spacing="1", align="center",
            ),
            rx.hstack(
                rx.text(value, font_size="22px", font_weight="800",
                        color=color),
                rx.text(unit, font_size="12px", color="#94a3b8",
                        align_self="flex-end"),
                spacing="1", align="baseline",
            ),
            spacing="1",
        ),
        bg="white",
        border_radius="10px",
        padding="16px",
        box_shadow="0 1px 3px rgba(0,0,0,.08)",
        min_width="140px",
        flex="1",
    )


def kpi_card_icon_box(
    label: str,
    value,
    unit: str = "",
    icon: str = "bar_chart_3",
    icon_color: str = "#38bd94",
    icon_bg: str = "#ecfdf5",
) -> rx.Component:
    """KPI 카드 — 아이콘 박스형 (업체관리자 스타일)
    아이콘이 원형 배경 안에 표시되고, 값이 크게 나타납니다.

    Args:
        label: 카드 제목
        value: 표시할 값
        unit: 단위
        icon: lucide 아이콘 이름
        icon_color: 아이콘 색상
        icon_bg: 아이콘 배경 색상
    """
    return rx.box(
        rx.vstack(
            rx.box(
                rx.icon(icon, size=20, color=icon_color),
                width="40px", height="40px", bg=icon_bg,
                border_radius="12px", display="flex",
                align_items="center", justify_content="center",
            ),
            rx.hstack(
                rx.text(value, font_size="26px", font_weight="800",
                        color="#0f172a", line_height="1"),
                rx.text(unit, font_size="12px", color="#64748b",
                        padding_bottom="3px"),
                align="end", spacing="1",
            ),
            rx.text(label, font_size="12px", color="#94a3b8",
                    font_weight="500"),
            spacing="3", align="start", width="100%",
        ),
        bg="white",
        border_radius="16px",
        padding="18px 16px",
        border="1px solid #e2e8f0",
        box_shadow="0 1px 4px rgba(0,0,0,0.04)",
        flex="1",
        min_width="130px",
    )


# ──────────────────────────────────────────
#  2. 섹션 헤더 (2가지 변형)
# ──────────────────────────────────────────

def section_header(
    icon: str,
    title: str,
    color: str = "#3b82f6",
) -> rx.Component:
    """섹션 헤더 — 기본형 (아이콘 + 제목)

    Args:
        icon: lucide 아이콘 이름
        title: 섹션 제목 텍스트
        color: 아이콘 색상 (기본: 파랑)
    """
    return rx.hstack(
        rx.icon(icon, size=18, color=color),
        rx.text(title, font_size="16px", font_weight="700",
                color="#1e293b"),
        spacing="2", align="center",
    )


def section_header_badge(
    icon: str,
    title: str,
    badge_val=None,
    color: str = "#38bd94",
) -> rx.Component:
    """섹션 헤더 — 배지 포함형 (업체관리자 스타일)
    제목 옆에 건수 등을 배지로 표시합니다.

    Args:
        icon: lucide 아이콘 이름
        title: 섹션 제목
        badge_val: 배지에 표시할 값 (None이면 배지 생략)
        color: 아이콘 색상 (기본: 초록)
    """
    items = [
        rx.icon(icon, size=16, color=color),
        rx.text(title, font_size="15px", font_weight="700",
                color="#1e293b"),
    ]
    if badge_val is not None:
        items.append(
            rx.badge(badge_val, color_scheme="green", size="1",
                     variant="soft")
        )
    return rx.hstack(*items, spacing="2", align="center")


# ──────────────────────────────────────────
#  3. 카드 래퍼
# ──────────────────────────────────────────

def card_box(*children, **kwargs) -> rx.Component:
    """공통 카드 래퍼 — 흰 배경 + 둥근 모서리 + 그림자
    모든 역할 페이지에서 콘텐츠를 감싸는 기본 카드입니다.

    Args:
        *children: 카드 안에 들어갈 컴포넌트들
        **kwargs: 추가 스타일 속성 (padding, width 등 오버라이드 가능)
    """
    defaults = dict(
        bg="white",
        border_radius="12px",
        padding="20px",
        border="1px solid #e2e8f0",
        box_shadow="0 2px 8px rgba(0,0,0,0.04)",
        width="100%",
    )
    defaults.update(kwargs)
    return rx.box(*children, **defaults)


def card_box_light(*children, **kwargs) -> rx.Component:
    """카드 래퍼 — 라이트형 (학교/교육청/급식 스타일)
    border 없이 shadow만 적용됩니다.
    """
    defaults = dict(
        bg="white",
        border_radius="12px",
        padding="20px",
        box_shadow="0 1px 3px rgba(0,0,0,.08)",
        width="100%",
    )
    defaults.update(kwargs)
    return rx.box(*children, **defaults)


# ──────────────────────────────────────────
#  4. 로고 박스
# ──────────────────────────────────────────

def logo_box() -> rx.Component:
    """ZERODA 로고 — 그래디언트 'Z' 아이콘 + 텍스트"""
    return rx.hstack(
        rx.box(
            rx.text("Z", font_size="15px", font_weight="800",
                    color="white"),
            width="34px",
            height="34px",
            bg="linear-gradient(135deg, #38bd94, #3b82f6)",
            border_radius="10px",
            display="flex",
            align_items="center",
            justify_content="center",
            box_shadow="0 4px 12px rgba(56,189,148,0.30)",
        ),
        rx.text(
            "ZERODA",
            font_size="17px",
            font_weight="800",
            background="linear-gradient(135deg, #0f172a, #334155)",
            background_clip="text",
            color="transparent",
        ),
        spacing="2",
        align="center",
    )


# ──────────────────────────────────────────
#  5. 빈 상태 표시
# ──────────────────────────────────────────

def empty_state(msg: str = "데이터가 없습니다") -> rx.Component:
    """빈 데이터일 때 보여주는 안내 컴포넌트

    Args:
        msg: 표시할 메시지
    """
    return rx.center(
        rx.vstack(
            rx.icon("inbox", size=32, color="#cbd5e1"),
            rx.text(msg, font_size="13px", color="#94a3b8"),
            spacing="2",
            align="center",
        ),
        padding_y="32px",
        width="100%",
    )


# ──────────────────────────────────────────
#  6. 테이블 헬퍼
# ──────────────────────────────────────────

def table_box(*children) -> rx.Component:
    """카드형 테이블 래퍼 — overflow:hidden으로 모서리 깔끔하게 처리

    Args:
        *children: 테이블 헤더 행 + 본문 등
    """
    return rx.box(
        *children,
        bg="white",
        border_radius="12px",
        border="1px solid #e2e8f0",
        box_shadow="0 1px 4px rgba(0,0,0,0.04)",
        overflow="hidden",
        width="100%",
    )


def table_header_row(*labels_flex) -> rx.Component:
    """테이블 헤더 행 — (라벨, flex) 튜플 리스트로 헤더를 생성합니다.

    사용법:
        table_header_row(("학교명", "2"), ("수거량", "1"), ("건수", "1"))

    Args:
        *labels_flex: (라벨텍스트, flex값) 튜플들
    """
    # 단일 문자열 호출 → rx.table용 column_header_cell 반환
    if len(labels_flex) == 1 and isinstance(labels_flex[0], str):
        return rx.table.column_header_cell(
            rx.text(labels_flex[0], font_size="12px", font_weight="700",
                    color="#64748b"),
        )
    # 튜플 리스트 → hstack 행
    cells = [
        rx.text(
            lbl,
            font_size="12px",
            font_weight="700",
            color="#64748b",
            flex=fx,
            text_align="left" if i == 0 else "right",
        )
        for i, (lbl, fx) in enumerate(labels_flex)
    ]
    return rx.box(
        rx.hstack(*cells, width="100%", padding_x="16px",
                  padding_y="10px"),
        bg="#f8fafc",
        border_bottom="1px solid #e2e8f0",
        border_radius="12px 12px 0 0",
    )


def col_header(text: str) -> rx.Component:
    """rx.table 전용 컬럼 헤더 셀 — 교육청/급식 페이지용

    Args:
        text: 컬럼 헤더 텍스트
    """
    return rx.table.column_header_cell(
        rx.text(text, font_size="12px", font_weight="700",
                color="#64748b")
    )


def table_cell(value, **props) -> rx.Component:
    """rx.table 전용 데이터 셀 — 교육청/급식 페이지용

    Args:
        value: 셀에 표시할 값
        **props: 추가 텍스트 속성
    """
    return rx.table.cell(rx.text(value, font_size="12px", **props))
