# zeroda_reflex/pages/driver.py
# 기사 대시보드 — 안전점검 → 수거일정 → 퇴근
import reflex as rx
from zeroda_reflex.state.driver_state import DriverState, SAFETY_CHECKLIST


def _header() -> rx.Component:
    """기사 대시보드 상단 헤더"""
    return rx.box(
        rx.vstack(
            rx.text(
                "ZERODA 기사앱",
                font_size="18px",
                font_weight="900",
                color="white",
            ),
            rx.text(
                DriverState.user_name + " 기사님",
                font_size="14px",
                color="rgba(255,255,255,0.85)",
            ),
            rx.text(
                DriverState.today_display,
                font_size="13px",
                color="rgba(255,255,255,0.7)",
            ),
            spacing="1",
            align="center",
        ),
        bg="linear-gradient(135deg, #1a73e8, #34a853)",
        padding="20px",
        border_radius="12px",
        text_align="center",
        width="100%",
    )


def _weather_section() -> rx.Component:
    """날씨 알림 섹션 (기상청 API 연동)"""
    return rx.cond(
        DriverState.weather_available,
        rx.box(
            rx.hstack(
                rx.text(
                    DriverState.weather_icon,
                    font_size="28px",
                ),
                rx.vstack(
                    rx.text(
                        DriverState.weather_summary,
                        font_size="13px",
                        font_weight="600",
                        color="#374151",
                    ),
                    rx.foreach(
                        DriverState.weather_alerts,
                        lambda a: rx.text(a, font_size="12px", color="#64748b"),
                    ),
                    spacing="1",
                    flex="1",
                ),
                align="start",
                spacing="3",
                width="100%",
            ),
            bg=rx.cond(
                DriverState.weather_level == "warning",
                "#fef2f2",
                rx.cond(
                    DriverState.weather_level == "caution",
                    "#fffbeb",
                    "#f0fdf4",
                ),
            ),
            border=rx.cond(
                DriverState.weather_level == "warning",
                "1px solid #fecaca",
                rx.cond(
                    DriverState.weather_level == "caution",
                    "1px solid #fde68a",
                    "1px solid #bbf7d0",
                ),
            ),
            border_radius="12px",
            padding="12px 16px",
            width="100%",
        ),
    )


def _safety_check_item(item_id: str, item_text: str) -> rx.Component:
    """개별 안전점검 항목"""
    return rx.hstack(
        rx.checkbox(
            item_text,
            checked=DriverState.checked_items[item_id],
            on_change=lambda _: DriverState.toggle_check(item_id),
            size="2",
        ),
        width="100%",
        padding_y="2px",
    )


def _safety_category(cat_key: str, cat_info: dict) -> rx.Component:
    """안전점검 카테고리"""
    return rx.vstack(
        rx.hstack(
            rx.text(
                f"{cat_info['icon']} {cat_info['label']}",
                font_weight="700",
                font_size="15px",
            ),
            rx.spacer(),
            rx.button(
                "✅전체",
                size="1",
                variant="ghost",
                on_click=DriverState.check_category(cat_key),
            ),
            width="100%",
        ),
        *[
            _safety_check_item(item["id"], item["text"])
            for item in cat_info["items"]
        ],
        spacing="1",
        width="100%",
        padding_y="8px",
    )


def _safety_section() -> rx.Component:
    """안전점검 섹션 — 완료/미완료 분기"""
    return rx.cond(
        DriverState.safety_done_today,
        # ── 완료 상태 ──
        rx.box(
            rx.hstack(
                rx.icon("circle_check", color="#34a853", size=20),
                rx.text(
                    rx.text.strong("일일 안전점검 완료"),
                    f" ({DriverState.safety_saved_time} 저장)",
                    font_size="15px",
                ),
            ),
            rx.text(
                "오늘 안전점검이 이미 완료되었습니다. 안전 운행하세요! 🚦",
                color="#34a853",
                font_size="14px",
                margin_top="8px",
            ),
            bg="#f0fdf4",
            border="1px solid #bbf7d0",
            border_radius="12px",
            padding="16px",
            width="100%",
        ),
        # ── 미완료 상태: 체크리스트 ──
        rx.vstack(
            rx.hstack(
                rx.icon("triangle_alert", color="#ea580c", size=20),
                rx.text(
                    "일일 안전보건 점검 (출발 전 필수)",
                    font_weight="700",
                    font_size="16px",
                ),
            ),
            rx.text(
                "산업안전보건법 제36조에 따른 위험성평가 기록물입니다.",
                font_size="12px",
                color="#64748b",
            ),

            # 전체 양호 / 전체 해제 버튼
            rx.hstack(
                rx.button(
                    "☑️ 전체 양호",
                    on_click=DriverState.check_all,
                    size="2",
                    variant="outline",
                    flex="1",
                ),
                rx.button(
                    "⬜ 전체 해제",
                    on_click=DriverState.uncheck_all,
                    size="2",
                    variant="outline",
                    flex="1",
                ),
                width="100%",
                spacing="2",
            ),

            # 카테고리별 체크리스트
            *[
                _safety_category(k, v)
                for k, v in SAFETY_CHECKLIST.items()
            ],

            # 진행률
            rx.progress(value=DriverState.safety_progress, width="100%"),
            rx.text(
                f"{DriverState.checked_count} / {DriverState.total_items} 항목 완료",
                font_size="12px",
                color="#64748b",
            ),

            # 완료/미완료 메시지
            rx.cond(
                DriverState.all_checked,
                rx.callout("모든 안전점검 완료! 안전 운행하세요. 🚦", icon="check", color_scheme="green"),
                rx.callout(
                    "미완료 항목을 확인해 주세요.",
                    icon="info",
                    color_scheme="orange",
                ),
            ),

            # 불량 메모
            rx.cond(
                ~DriverState.all_checked,
                rx.text_area(
                    placeholder="불량/미점검 항목 조치사항 (예: 유압호스 누유 → 정비 예약)",
                    on_change=DriverState.set_fail_memo,
                    width="100%",
                    rows="3",
                ),
            ),

            # 저장 버튼
            rx.button(
                "💾 점검 결과 저장",
                on_click=DriverState.save_safety_check,
                width="100%",
                size="3",
                color_scheme="blue",
            ),

            spacing="3",
            width="100%",
            bg="white",
            border_radius="12px",
            padding="16px",
            box_shadow="0 2px 8px rgba(0,0,0,0.06)",
        ),
    )


def _collection_section() -> rx.Component:
    """수거입력 섹션 — 진행률 + 완료/미완료 거래처 + 삭제 기능"""
    return rx.vstack(
        rx.hstack(
            rx.icon("truck", size=20, color="#1a73e8"),
            rx.text("수거입력", font_weight="700", font_size="16px"),
            rx.spacer(),
            rx.badge(
                f"오늘 {DriverState.today_collection_count}건 / {DriverState.today_total_weight}kg",
                color_scheme="blue",
                size="1",
            ),
        ),

        # ── 수거 진행률 ──
        rx.vstack(
            rx.hstack(
                rx.text(
                    DriverState.collection_progress_text,
                    font_size="13px",
                    font_weight="600",
                    color="#374151",
                ),
                rx.spacer(),
                rx.cond(
                    DriverState.all_collected,
                    rx.badge("전체 완료", color_scheme="green", size="1"),
                    rx.badge("진행 중", color_scheme="orange", size="1"),
                ),
                width="100%",
            ),
            rx.progress(value=DriverState.collection_progress_pct, width="100%"),
            spacing="1",
            width="100%",
        ),

        # ── 미완료 거래처 표시 ──
        rx.cond(
            DriverState.remaining_schools.length() > 0,
            rx.box(
                rx.text("미수거 거래처", font_size="12px", font_weight="600", color="#dc2626"),
                rx.hstack(
                    rx.foreach(
                        DriverState.remaining_schools,
                        lambda s: rx.badge(s, color_scheme="red", variant="outline", size="1"),
                    ),
                    wrap="wrap",
                    spacing="1",
                ),
                bg="#fef2f2",
                border="1px solid #fecaca",
                border_radius="8px",
                padding="8px 12px",
                width="100%",
            ),
        ),

        # ── 거래처 선택 ──
        rx.text("거래처", font_size="13px", font_weight="600", color="#374151"),
        rx.select(
            DriverState.assigned_schools,
            value=DriverState.selected_school,
            on_change=DriverState.set_selected_school,
            placeholder="거래처를 선택하세요",
            width="100%",
        ),

        # ── 품목 선택 ──
        rx.text("품목", font_size="13px", font_weight="600", color="#374151"),
        rx.radio_group(
            ["음식물", "재활용", "일반"],
            value=DriverState.collection_item_type,
            on_change=DriverState.set_collection_item_type,
            direction="row",
            spacing="4",
        ),

        # ── 수거량 입력 ──
        rx.text("수거량 (kg)", font_size="13px", font_weight="600", color="#374151"),
        rx.input(
            placeholder="예: 52.5",
            value=DriverState.collection_weight,
            on_change=DriverState.set_collection_weight,
            type="number",
            width="100%",
            size="3",
        ),

        # ── 저장 버튼 ──
        rx.button(
            "📥 수거 저장",
            on_click=DriverState.save_collection_entry,
            width="100%",
            size="3",
            color_scheme="blue",
        ),

        # ── 저장/삭제 메시지 ──
        rx.cond(
            DriverState.collection_save_msg != "",
            rx.text(
                DriverState.collection_save_msg,
                font_size="13px",
                color=rx.cond(
                    DriverState.collection_save_msg.contains("완료"),
                    "#16a34a",
                    "#dc2626",
                ),
            ),
        ),

        # ── 오늘 수거 기록 (삭제 버튼 포함) ──
        rx.cond(
            DriverState.today_collection_count > 0,
            rx.vstack(
                rx.text("오늘 수거 기록", font_size="13px", font_weight="600", color="#374151"),
                rx.foreach(
                    DriverState.today_collections,
                    lambda c: rx.hstack(
                        rx.text(c["school_name"], font_size="13px", flex="1"),
                        rx.badge(c["item_type"], size="1"),
                        rx.text(f'{c["weight"]}kg', font_size="13px", font_weight="600"),
                        rx.icon_button(
                            rx.icon("trash_2", size=14),
                            size="1",
                            variant="ghost",
                            color_scheme="red",
                            on_click=DriverState.delete_collection_entry(c["rowid"]),
                        ),
                        width="100%",
                        padding_y="4px",
                        border_bottom="1px solid #f1f5f9",
                        align="center",
                    ),
                ),
                width="100%",
                spacing="1",
            ),
        ),

        spacing="3",
        width="100%",
        bg="white",
        border_radius="12px",
        padding="16px",
        box_shadow="0 2px 8px rgba(0,0,0,0.06)",
    )


def _checkout_section() -> rx.Component:
    """퇴근 섹션"""
    return rx.vstack(
        rx.hstack(
            rx.icon("home", size=20, color="#1a73e8"),
            rx.text("퇴근", font_weight="700", font_size="16px"),
        ),
        rx.cond(
            DriverState.is_checked_out,
            # ── 퇴근 완료 상태 ──
            rx.box(
                rx.hstack(
                    rx.icon("circle_check", color="#16a34a", size=20),
                    rx.text(
                        rx.text.strong("퇴근 완료"),
                        f" ({DriverState.checkout_time})",
                        font_size="15px",
                    ),
                ),
                rx.text(
                    "오늘도 수고하셨습니다! 안전 귀가하세요.",
                    color="#16a34a",
                    font_size="14px",
                    margin_top="8px",
                ),
                bg="#f0fdf4",
                border="1px solid #bbf7d0",
                border_radius="12px",
                padding="16px",
                width="100%",
            ),
            # ── 퇴근 미완료 ──
            rx.vstack(
                rx.text(
                    f"오늘 수거: {DriverState.today_collection_count}건 / {DriverState.today_total_weight}kg",
                    font_size="14px",
                    color="#64748b",
                ),
                rx.button(
                    "🏠 퇴근하기",
                    on_click=DriverState.do_checkout,
                    width="100%",
                    size="3",
                    color_scheme="green",
                ),
                spacing="3",
                width="100%",
            ),
        ),
        spacing="3",
        width="100%",
        bg="white",
        border_radius="12px",
        padding="16px",
        box_shadow="0 2px 8px rgba(0,0,0,0.06)",
    )


def driver_page() -> rx.Component:
    """기사 대시보드 메인 페이지"""
    return rx.box(
        rx.vstack(
            _header(),
            _weather_section(),
            _safety_section(),
            _collection_section(),
            _checkout_section(),

            # 로그아웃
            rx.button(
                "로그아웃",
                on_click=DriverState.logout,
                variant="ghost",
                size="2",
                color="#94a3b8",
                width="100%",
            ),

            spacing="4",
            width="100%",
            max_width="500px",
            margin="0 auto",
            padding="16px",
        ),
        bg="#f1f5f9",
        min_height="100vh",
    )
