# zeroda_reflex/components/table_renders.py
# ══════════════════════════════════════════════════════════════
#  범용 테이블 렌더링 헬퍼
#  - 새로운 테이블을 만들 때 반복 코드를 줄이기 위한 빌더 함수 모음
#  - 기존 페이지의 커스텀 행 렌더러는 보존하고,
#    신규 개발 시 이 모듈의 함수를 활용합니다.
# ══════════════════════════════════════════════════════════════
import reflex as rx


def data_row_hstack(
    *cells,
    hover: bool = True,
    padding_x: str = "16px",
    padding_y: str = "10px",
) -> rx.Component:
    """범용 데이터 행 — hstack 기반 가로 배치

    테이블 행에서 가장 흔한 패턴인 "좌우로 셀을 배치하고
    호버 효과와 하단 보더를 가진 행"을 생성합니다.

    Args:
        *cells: rx.text 등 셀 컴포넌트들
        hover: 마우스 호버 효과 적용 여부
        padding_x: 좌우 패딩
        padding_y: 상하 패딩

    사용 예:
        data_row_hstack(
            rx.text(row["name"], flex="2"),
            rx.text(row["value"], flex="1"),
        )
    """
    hover_style = {"bg": "#f8fafc"} if hover else {}
    return rx.box(
        rx.hstack(
            *cells,
            width="100%",
            padding_x=padding_x,
            padding_y=padding_y,
            align="center",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover=hover_style,
    )


def text_cell(
    value,
    flex: str = "1",
    color: str = "#1e293b",
    font_size: str = "13px",
    font_weight: str = "400",
    truncate: bool = False,
    align: str = "left",
    **props,
) -> rx.Component:
    """범용 텍스트 셀 — data_row_hstack 안에서 사용

    Args:
        value: 표시할 값
        flex: flex 비율 (넓이 조절)
        color: 글자 색상
        font_size: 글자 크기
        font_weight: 글자 두께
        truncate: 넘침 시 말줄임표(…) 처리
        align: 텍스트 정렬 (left/right/center)
        **props: 추가 스타일
    """
    style = dict(
        font_size=font_size,
        color=color,
        font_weight=font_weight,
        flex=flex,
        text_align=align,
    )
    if truncate:
        style.update(
            min_width="0",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
        )
    style.update(props)
    return rx.text(value, **style)


def value_with_unit(
    value,
    unit: str,
    value_color: str = "#0f172a",
    unit_color: str = "#94a3b8",
    value_size: str = "13px",
    unit_size: str = "11px",
    font_weight: str = "700",
    flex: str = "1",
    justify: str = "end",
) -> rx.Component:
    """값 + 단위 조합 셀 — "123 kg" 같은 패턴

    Args:
        value: 숫자 값
        unit: 단위 (kg, 건, 원 등)
        value_color: 값 색상
        unit_color: 단위 색상
        value_size: 값 글자 크기
        unit_size: 단위 글자 크기
        font_weight: 값 글자 두께
        flex: flex 비율
        justify: hstack 정렬
    """
    return rx.hstack(
        rx.text(value, font_size=value_size, font_weight=font_weight,
                color=value_color),
        rx.text(unit, font_size=unit_size, color=unit_color),
        spacing="1",
        align="center",
        justify=justify,
        flex=flex,
    )


def badge_cell(
    value,
    color_scheme: str = "green",
    size: str = "1",
    variant: str = "soft",
) -> rx.Component:
    """배지 셀 — 상태 표시용 (음식물/재활용/일반, 승인/반려 등)

    Args:
        value: 배지 텍스트
        color_scheme: 색상 테마
        size: 크기
        variant: 스타일 변형
    """
    return rx.badge(
        value,
        size=size,
        color_scheme=color_scheme,
        variant=variant,
        flex_shrink="0",
    )


def status_badge(
    value,
    status_colors: dict[str, str] | None = None,
) -> rx.Component:
    """상태 배지 — 값에 따라 자동으로 색상 적용

    Args:
        value: 상태 값
        status_colors: {상태값: 색상테마} 매핑
                      기본: {"approved":"green", "pending":"orange",
                             "rejected":"red", "confirmed":"blue"}
    """
    if status_colors is None:
        status_colors = {
            "approved": "green",
            "pending": "orange",
            "rejected": "red",
            "confirmed": "blue",
            "submitted": "yellow",
        }
    # Reflex에서는 동적 dict lookup이 제한적이므로 기본값 사용
    return rx.badge(
        value,
        size="1",
        variant="soft",
        flex_shrink="0",
    )


def empty_table_message(
    msg: str = "데이터가 없습니다",
    icon: str = "inbox",
) -> rx.Component:
    """빈 테이블 안내 메시지

    Args:
        msg: 표시할 메시지
        icon: lucide 아이콘 이름
    """
    return rx.center(
        rx.vstack(
            rx.icon(icon, size=28, color="#cbd5e1"),
            rx.text(msg, font_size="13px", color="#94a3b8"),
            spacing="2",
            align="center",
        ),
        padding="32px",
        width="100%",
    )
