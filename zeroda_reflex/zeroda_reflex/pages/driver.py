# zeroda_reflex/pages/driver.py
# 기사 대시보드 — 안전점검 → 수거일정 → 퇴근
import reflex as rx
from zeroda_reflex.state.driver_state import DriverState, SAFETY_CHECKLIST
from zeroda_reflex.state.auth_state import AuthState


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
                DriverState.user_name.to(str) + " 기사님",
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
                    rx.cond(
                        DriverState.weather_location != "",
                        rx.text(
                            "📍 ",
                            DriverState.weather_location,
                            font_size="11px",
                            color="#6b7280",
                            font_weight="500",
                        ),
                    ),
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


def _schoolzone_warning() -> rx.Component:
    """수거입력 섹션 내 스쿨존 원형 시각 경고 — 학교(🏫) 거래처 선택 시 표시"""
    return rx.hstack(
        rx.box(
            rx.text(
                "30",
                color="white",
                font_weight="bold",
                font_size="20px",
                line_height="1",
            ),
            border_radius="50%",
            background="red",
            width="48px",
            height="48px",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.text(
            "스쿨존 서행",
            font_size="14px",
            font_weight="600",
            color="#dc2626",
        ),
        align="center",
        spacing="2",
        padding="6px 0",
    )


def _schoolzone_section() -> rx.Component:
    """스쿨존 알림 토글"""
    return rx.box(
        rx.hstack(
            rx.text("🚸", font_size="20px"),
            rx.vstack(
                rx.text("스쿨존 알림", font_weight="600", font_size="14px"),
                rx.text(
                    "스쿨존 구역 진입 시 서행 알림",
                    font_size="12px",
                    color="#64748b",
                ),
                spacing="0",
                flex="1",
            ),
            rx.switch(
                checked=DriverState.schoolzone_enabled,
                on_change=DriverState.toggle_schoolzone,
            ),
            align="center",
            spacing="3",
            width="100%",
        ),
        rx.cond(
            DriverState.schoolzone_enabled,
            rx.box(
                rx.text(
                    "🚨 스쿨존 진입 시 속도를 30km/h 이하로 줄이세요!",
                    font_size="13px",
                    font_weight="600",
                    color="#dc2626",
                ),
                bg="#fef2f2",
                border="1px solid #fecaca",
                border_radius="8px",
                padding="8px 12px",
                margin_top="8px",
                width="100%",
            ),
        ),
        bg="white",
        border_radius="12px",
        padding="12px 16px",
        box_shadow="0 2px 8px rgba(0,0,0,0.06)",
        width="100%",
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
    """안전점검 섹션 — 접힘/완료/미완료 3단 분기"""
    return rx.cond(
        DriverState.safety_panel_collapsed,
        # ── 접힌 상태: 완료 후 자동 축소 ──
        rx.box(
            rx.hstack(
                rx.icon("circle_check", color="#34a853", size=18),
                rx.text(
                    rx.text.strong("일일 안전점검 완료"),
                    f" ({DriverState.safety_saved_time} 저장)",
                    font_size="14px",
                ),
                rx.spacer(),
                rx.button(
                    "다시 보기 ▼",
                    on_click=DriverState.toggle_safety_panel,
                    size="1",
                    variant="ghost",
                    color="#34a853",
                ),
                width="100%",
                align="center",
            ),
            bg="#f0fdf4",
            border="1px solid #bbf7d0",
            border_radius="12px",
            padding="12px 16px",
            width="100%",
        ),
        # ── 펼친 상태 ──
        rx.cond(
            DriverState.safety_done_today,
            # ── 완료 상태 (펼쳐짐) ──
            rx.box(
                rx.hstack(
                    rx.icon("circle_check", color="#34a853", size=20),
                    rx.text(
                        rx.text.strong("일일 안전점검 완료"),
                        f" ({DriverState.safety_saved_time} 저장)",
                        font_size="15px",
                    ),
                    rx.spacer(),
                    rx.button(
                        "접기 ▲",
                        on_click=DriverState.toggle_safety_panel,
                        size="1",
                        variant="ghost",
                    ),
                    width="100%",
                    align="center",
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
                disabled=~AuthState.is_user_active,
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
        ),  # ← 내부 rx.cond(safety_done_today, ...) 닫기
    )       # ← 외부 rx.cond(safety_panel_collapsed, ...) 닫기


def _row_input(school_idx, row_idx, row) -> rx.Component:
    """수거 입력 행 — 날짜/품목/kg/메모/삭제
    school_idx: 외부 foreach Var (거래처 인덱스)
    row_idx: 내부 foreach Var (행 인덱스)
    row: 행 dict {"date", "item_type", "weight", "memo"}
    """
    return rx.hstack(
        rx.input(
            value=row["date"],
            on_change=lambda v: DriverState.set_school_row_date([school_idx, row_idx, v]),
            type="date",
            size="1",
            width="128px",
            flex_shrink="0",
        ),
        rx.select(
            ["음식물", "재활용", "일반"],
            value=row["item_type"],
            on_change=lambda v: DriverState.set_school_row_item_type([school_idx, row_idx, v]),
            size="1",
            width="82px",
            flex_shrink="0",
        ),
        rx.input(
            placeholder="kg",
            value=row["weight"],
            on_change=lambda v: DriverState.set_school_row_weight([school_idx, row_idx, v]),
            type="number",
            input_mode="decimal",
            size="1",
            width="68px",
            flex_shrink="0",
        ),
        rx.input(
            placeholder="메모",
            value=row["memo"],
            on_change=lambda v: DriverState.set_school_row_memo([school_idx, row_idx, v]),
            size="1",
            flex="1",
            min_width="0",
        ),
        rx.icon_button(
            rx.icon("x", size=12),
            size="1",
            variant="ghost",
            color_scheme="red",
            on_click=DriverState.remove_row_for_school([school_idx, row_idx]),
            disabled=~AuthState.is_user_active,
            flex_shrink="0",
        ),
        width="100%",
        spacing="1",
        align="center",
    )


def _schedule_school_card(s: dict, idx) -> rx.Component:
    """일정 학교 카드 — 수거입력 통합 (완료 시 녹색, 미완료 시 다일자 행 입력폼 표시)
    idx: foreach 인덱스 (Var)
    s["rows"]: 행 리스트 [{"date","item_type","weight","memo"}]
    s["save_msg"], s["photo_msg"]: 카드 레벨 메시지
    """
    school_name = s["school_name"]
    items_text = s["items"]
    address = s["address"]
    icon = s["icon"]
    is_done = DriverState.collected_schools.contains(school_name)

    return rx.cond(
        is_done,
        # ── 완료 항목: 한 줄 축약 카드 ──
        rx.hstack(
            rx.icon("circle_check", color="#16a34a", size=14),
            rx.text(school_name, font_size="13px", font_weight="600", color="#6b7280"),
            rx.text(items_text, font_size="11px", color="#9ca3af"),
            rx.spacer(),
            rx.badge("✓ 완료", color_scheme="green", variant="soft", size="1"),
            width="100%",
            align="center",
            spacing="2",
            padding="6px 10px",
            bg="#f9fafb",
            border="1px solid #d1fae5",
            border_radius="8px",
        ),
        # ── 미완료 항목: 기존 풀카드 ──
        rx.vstack(
        # ── 거래처 정보 헤더 ──
        rx.hstack(
            rx.cond(
                is_done,
                rx.icon("circle_check", color="#16a34a", size=16),
                rx.icon("circle", color="#d1d5db", size=16),
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(icon, font_size="15px"),
                    rx.text(
                        school_name,
                        font_size="14px",
                        font_weight="700",
                        color=rx.cond(is_done, "#16a34a", "#374151"),
                    ),
                    spacing="1",
                    align="center",
                ),
                rx.text(
                    items_text,
                    font_size="12px",
                    color="#64748b",
                ),
                spacing="0",
                flex="1",
            ),
            rx.cond(
                is_done,
                rx.badge("✅완료", color_scheme="green", size="1"),
                rx.badge("미수거", color_scheme="gray", variant="outline", size="1"),
            ),
            width="100%",
            align="center",
            spacing="3",
        ),

        # ── 지도 네비게이션 링크 ──
        rx.cond(
            address != "",
            rx.hstack(
                rx.link(
                    rx.badge("🗺️카카오", color_scheme="yellow", size="1"),
                    href="https://map.kakao.com/link/search/" + address.to(str),
                    is_external=True,
                ),
                rx.link(
                    rx.badge("🚗T맵", color_scheme="blue", size="1"),
                    href="https://tmap.life/search?name=" + address.to(str),
                    is_external=True,
                ),
                rx.link(
                    rx.badge("🟢네이버", color_scheme="green", size="1"),
                    href="https://map.naver.com/v5/search/" + address.to(str),
                    is_external=True,
                ),
                spacing="2",
                width="100%",
            ),
        ),

        # ── 스쿨존 경고 (🏫 학교 거래처만) ──
        rx.cond(
            icon == "🏫",
            _schoolzone_warning(),
            rx.fragment(),
        ),

        # ── 수거 입력 영역 (미완료 시만 표시) ──
        rx.cond(
            ~is_done,
            rx.vstack(
                rx.divider(color="#e5e7eb", margin_y="4px"),

                # ── 컬럼 헤더 ──
                rx.hstack(
                    rx.text("📅 날짜", font_size="11px", color="#9ca3af", width="128px", flex_shrink="0"),
                    rx.text("품목", font_size="11px", color="#9ca3af", width="82px", flex_shrink="0"),
                    rx.text("kg", font_size="11px", color="#9ca3af", width="68px", flex_shrink="0"),
                    rx.text("메모", font_size="11px", color="#9ca3af", flex="1"),
                    rx.box(width="28px", flex_shrink="0"),
                    width="100%",
                    spacing="1",
                ),

                # ── 행 목록 (다일자 입력) — .to(list[dict])로 타입 명시 필수 ──
                rx.foreach(s["rows"].to(list[dict]), lambda r, ridx: _row_input(idx, ridx, r)),

                # ── + 행 추가 / 음성 ──
                rx.hstack(
                    rx.button(
                        "+ 행 추가",
                        on_click=DriverState.add_row_for_school(idx),
                        disabled=~AuthState.is_user_active,
                        size="1",
                        variant="ghost",
                        color_scheme="blue",
                    ),
                    rx.spacer(),
                    width="100%",
                    align="center",
                ),

                # 사진 첨부 + 위치설정
                rx.hstack(
                    rx.button(
                        rx.cond(
                            DriverState.show_photo_for == s["school_name"],
                            "📷 사진 닫기",
                            "📷 사진 첨부",
                        ),
                        on_click=DriverState.toggle_photo_panel(idx),
                        size="1",
                        variant="outline",
                        color_scheme="orange",
                    ),
                    rx.button(
                        "📍 위치설정",
                        on_click=DriverState.initiate_location_for_school(idx),
                        disabled=~AuthState.is_user_active,
                        size="1",
                        variant="outline",
                        color_scheme="violet",
                    ),
                    rx.cond(
                        s["photo_msg"] != "",
                        rx.text(s["photo_msg"], font_size="11px", color="#16a34a"),
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
                # 사진 업로드 패널 (열린 카드만 DOM에 render됨 → ID 충돌 없음)
                rx.cond(
                    DriverState.show_photo_for == s["school_name"],
                    rx.vstack(
                        rx.text_area(
                            value=s["photo_remark"].to(str),
                            placeholder="특이사항 코멘트 (선택) — 예: 음식물 이물질, 용기 파손, 출입 문제 등",
                            on_change=lambda v: DriverState.set_photo_remark([idx, v]),
                            size="1",
                            rows="2",
                            width="100%",
                            font_size="12px",
                        ),
                        rx.upload(
                            rx.button(
                                "📂 파일 선택 (1장)",
                                size="1",
                                variant="soft",
                                width="100%",
                            ),
                            id="active_card_photo",
                            accept={"image/*": [".jpg", ".jpeg", ".png"]},
                            max_files=1,
                            multiple=False,
                        ),
                        rx.button(
                            "📤 업로드",
                            on_click=DriverState.handle_card_photo_upload(
                                rx.upload_files(upload_id="active_card_photo")
                            ),
                            disabled=~AuthState.is_user_active,
                            size="1",
                            color_scheme="orange",
                            width="100%",
                        ),
                        bg="#fff7ed",
                        border="1px solid #fed7aa",
                        border_radius="6px",
                        padding="8px",
                        spacing="2",
                        width="100%",
                    ),
                ),

                # 저장 버튼 2개 (idx로 핸들러 호출)
                rx.hstack(
                    rx.button(
                        "📋 임시저장",
                        on_click=DriverState.initiate_draft_for_school(idx),
                        disabled=~AuthState.is_user_active,
                        size="2",
                        variant="outline",
                        color_scheme="gray",
                        flex="1",
                    ),
                    rx.button(
                        "✅ 수거완료",
                        on_click=DriverState.initiate_save_for_school(idx),
                        disabled=~AuthState.is_user_active,
                        size="2",
                        color_scheme="blue",
                        flex="1",
                    ),
                    width="100%",
                    spacing="2",
                ),

                # 저장 결과 메시지 (s["save_msg"] 직접 접근)
                rx.cond(
                    s["save_msg"] != "",
                    rx.text(s["save_msg"], font_size="12px", color="#374151"),
                ),

                spacing="2",
                width="100%",
            ),
        ),

        width="100%",
        padding="10px 12px",
        bg="white",
        border="1px solid #e5e7eb",
        border_radius="8px",
        spacing="2",
        ),
    )


def _voice_pick_candidate_row(c: dict) -> rx.Component:
    """GPS 복수 후보 선택 다이얼로그 — 개별 거래처 버튼 행"""
    return rx.button(
        rx.hstack(
            rx.icon("map_pin", size=14, color="#16a34a"),
            rx.text(c["name"], font_size="14px", font_weight="600", color="#1e293b"),
            rx.spacer(),
            rx.badge(
                rx.text(c["distance_m"].to(str), "m", as_="span"),
                color_scheme="green", variant="soft", size="1",
            ),
            width="100%",
            align="center",
            spacing="2",
        ),
        on_click=DriverState.pick_voice_candidate(c["name"]),
        variant="outline",
        width="100%",
        cursor="pointer",
        color_scheme="gray",
    )


def _voice_pick_dialog() -> rx.Component:
    """GPS 복수 후보 선택 다이얼로그"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("거래처를 선택하세요"),
            rx.dialog.description(
                rx.hstack(
                    rx.icon("map_pin", size=14, color="#64748b"),
                    rx.text(
                        "현재 위치 반경 내 ",
                        rx.text.strong(DriverState.voice_pick_candidates.length().to(str)),
                        "개의 거래처가 등록되어 있습니다.",
                        font_size="13px",
                        color="#64748b",
                    ),
                    spacing="1",
                    align="center",
                ),
                margin_bottom="12px",
            ),
            rx.vstack(
                rx.foreach(
                    DriverState.voice_pick_candidates,
                    _voice_pick_candidate_row,
                ),
                spacing="2",
                width="100%",
            ),
            rx.divider(margin_y="12px"),
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "취소",
                        on_click=DriverState.cancel_voice_pick,
                        variant="ghost",
                        color_scheme="gray",
                        size="2",
                        cursor="pointer",
                    ),
                ),
                justify="end",
                width="100%",
            ),
            max_width="400px",
        ),
        open=DriverState.voice_pick_open,
        on_open_change=DriverState.on_voice_pick_open_change,
    )


def _voice_confirm_dialog() -> rx.Component:
    """음성 인식 결과 확인 다이얼로그 — 항상 표시 (성공/실패 무관)
    섹션 1: 정규화된 텍스트 표시
    섹션 2: 매칭 실패 시 실패 안내 + 다시 말하기만 노출
    섹션 4: '다시 말하기' 버튼
    섹션 6: GPS·일정기반 배지
    """
    return rx.dialog.root(
        rx.dialog.content(
            # ── 제목 (성공/실패 조건부) ──
            rx.dialog.title(
                rx.cond(
                    DriverState.voice_match_failed,
                    "🎤 음성 인식 — 매칭 실패",
                    "🎤 음성 인식 결과 확인",
                )
            ),
            # ── 원본 + 정규화 텍스트 (항상 표시) ──
            rx.text(
                "인식: ",
                rx.text.strong(DriverState.voice_pending_raw),
                size="2",
                color="#64748b",
            ),
            rx.cond(
                DriverState.voice_normalized_text != DriverState.voice_pending_raw,
                rx.text(
                    "정규화: ",
                    rx.text.strong(DriverState.voice_normalized_text),
                    size="2",
                    color="#7c3aed",
                ),
                rx.fragment(),
            ),
            rx.divider(),
            # ── 본문: 실패 안내 vs 성공 목록 ──
            rx.cond(
                DriverState.voice_match_failed,
                # 섹션 2: 매칭 실패 안내
                rx.vstack(
                    rx.badge("매칭 실패", color_scheme="red", size="2"),
                    rx.text(
                        "거래처·날짜·수거량을 인식하지 못했습니다. 다시 말씀해 주세요.",
                        size="2",
                        color="#64748b",
                    ),
                    spacing="2",
                    align="start",
                    padding_y="8px",
                ),
                # 성공: 입력될 항목 목록
                rx.vstack(
                    rx.heading("입력될 항목", size="3"),
                    rx.foreach(
                        DriverState.voice_pending_entries,
                        lambda e: rx.hstack(
                            rx.icon("check", color="green", size=16),
                            rx.text(e["school"], weight="bold", size="2"),
                            rx.text(e["date"], size="2", color="#64748b"),
                            rx.text(e["weight"], "kg", size="2", color_scheme="grass"),
                            # 섹션 1: 일정기반 배지
                            rx.cond(
                                e.get("schedule_matched", False),
                                rx.badge(
                                    "📅 일정기반",
                                    color_scheme="blue",
                                    size="1",
                                    variant="soft",
                                ),
                                rx.fragment(),
                            ),
                            # 섹션 6: GPS 매칭 배지
                            rx.cond(
                                e.get("gps_matched", False),
                                rx.badge(
                                    "📍 GPS 기반",
                                    color_scheme="violet",
                                    size="1",
                                    variant="soft",
                                ),
                                rx.fragment(),
                            ),
                            spacing="3",
                            align="center",
                        ),
                    ),
                    rx.cond(
                        DriverState.voice_pending_failed.length() > 0,
                        rx.vstack(
                            rx.divider(),
                            rx.text("⚠️ 인식 실패:", color="red", size="2"),
                            rx.foreach(
                                DriverState.voice_pending_failed,
                                lambda f: rx.text("· ", f, size="2", color="#94a3b8"),
                            ),
                            spacing="1",
                            align="start",
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    align="stretch",
                ),
            ),
            # ── 버튼 영역 ──
            rx.hstack(
                rx.dialog.close(
                    rx.button(
                        "취소",
                        variant="soft",
                        color_scheme="gray",
                        on_click=DriverState.cancel_voice_apply,
                    ),
                ),
                # 섹션 4: 다시 말하기 버튼 (항상 노출)
                rx.button(
                    "🎤 다시 말하기",
                    variant="soft",
                    color_scheme="blue",
                    on_click=DriverState.retry_voice_recognition,
                ),
                # 확인 버튼: 성공 시만 노출
                rx.cond(
                    DriverState.voice_match_failed,
                    rx.fragment(),
                    rx.dialog.close(
                        rx.button(
                            "✅ 확인하고 입력",
                            color_scheme="grass",
                            on_click=DriverState.confirm_voice_apply,
                            disabled=~AuthState.is_user_active,
                        ),
                    ),
                ),
                spacing="3",
                justify="end",
                margin_top="1em",
                flex_wrap="wrap",
            ),
            max_width="500px",
        ),
        open=DriverState.voice_confirm_open,
        on_open_change=DriverState.cancel_voice_apply,
    )


def _schedule_section() -> rx.Component:
    """수거일정 섹션 — 날짜 선택 → 배정 학교 목록"""
    return rx.vstack(
        # 헤더
        rx.hstack(
            rx.icon("calendar", size=20, color="#1a73e8"),
            rx.text("수거일정", font_weight="700", font_size="16px"),
            rx.spacer(),
            rx.badge(
                DriverState.schedule_total.to(str) + "개 거래처",
                color_scheme="blue",
                size="1",
            ),
        ),

        # 날짜 선택
        rx.hstack(
            rx.input(
                value=DriverState.schedule_date,
                on_change=DriverState.set_schedule_date,
                type="date",
                flex="1",
                size="2",
            ),
            rx.button(
                "오늘",
                on_click=DriverState.set_schedule_today,
                size="2",
                variant="outline",
            ),
            width="100%",
            spacing="2",
        ),

        # 선택 날짜 표시
        rx.text(
            DriverState.schedule_date_display,
            font_size="13px",
            color="#64748b",
        ),

        rx.text(
            "우측 상단 🎤 버튼으로 음성 입력 — 예: '6일 서초고 204, 17일 서초고 200'",
            font_size="11px",
            color="#94a3b8",
            text_align="center",
        ),

        # 일정이 있을 때
        rx.cond(
            DriverState.schedule_total > 0,
            rx.vstack(
                # 진행 요약
                rx.hstack(
                    rx.text(
                        "완료 " + DriverState.schedule_done_schools.length().to(str)
                        + " / 전체 " + DriverState.schedule_total.to(str),
                        font_size="13px",
                        font_weight="600",
                        color="#374151",
                    ),
                    rx.spacer(),
                    rx.cond(
                        DriverState.schedule_remaining_schools.length() == 0,
                        rx.badge("전체 완료", color_scheme="green", size="1"),
                        rx.badge("진행 중", color_scheme="orange", size="1"),
                    ),
                    width="100%",
                ),
                # 수거 진행률 바
                rx.progress(value=DriverState.collection_progress_pct, width="100%"),
                # 학교 카드 목록 (각 카드에 수거입력 통합 — idx로 schedule_schools 업데이트)
                rx.foreach(
                    DriverState.schedule_schools,
                    lambda s, idx: _schedule_school_card(s, idx),
                ),
                spacing="2",
                width="100%",
            ),
            # 일정 없을 때
            rx.box(
                rx.text(
                    "해당 날짜에 수거 일정이 없습니다.",
                    font_size="13px",
                    color="#64748b",
                    text_align="center",
                ),
                bg="#f8fafc",
                border="1px dashed #d1d5db",
                border_radius="8px",
                padding="20px",
                width="100%",
            ),
        ),

        # ── 최근 수거 기록 (기간 필터 + 삭제) ──
        rx.vstack(
            rx.divider(),
            rx.hstack(
                rx.text(
                    "📋 최근 수거 기록",
                    font_size="13px",
                    font_weight="600",
                    color="#374151",
                ),
                rx.spacer(),
                rx.badge(
                    DriverState.record_filter_label.to(str) + ": "
                    + DriverState.recent_collection_count.to(str) + "건",
                    color_scheme="blue",
                    size="1",
                ),
                rx.icon_button(
                    rx.cond(
                        DriverState.recent_expanded,
                        rx.icon("chevron_up", size=14),
                        rx.icon("chevron_down", size=14),
                    ),
                    on_click=DriverState.toggle_recent_expanded,
                    size="1",
                    variant="ghost",
                    color_scheme="gray",
                    cursor="pointer",
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                DriverState.recent_expanded,
                rx.vstack(
                rx.hstack(
                rx.button(
                    "오늘",
                    size="1",
                    variant=rx.cond(DriverState.record_filter == "today", "solid", "soft"),
                    on_click=DriverState.set_record_filter("today"),
                ),
                rx.button(
                    "최근 7일",
                    size="1",
                    variant=rx.cond(DriverState.record_filter == "7days", "solid", "soft"),
                    on_click=DriverState.set_record_filter("7days"),
                ),
                rx.button(
                    "최근 30일",
                    size="1",
                    variant=rx.cond(DriverState.record_filter == "30days", "solid", "soft"),
                    on_click=DriverState.set_record_filter("30days"),
                ),
                rx.button(
                    "이번 달",
                    size="1",
                    variant=rx.cond(DriverState.record_filter == "month", "solid", "soft"),
                    on_click=DriverState.set_record_filter("month"),
                ),
                rx.select(
                    DriverState.customer_filter_options_all,
                    value=rx.cond(DriverState.customer_filter == "", "전체", DriverState.customer_filter),
                    on_change=DriverState.set_customer_filter,
                    size="1",
                    placeholder="거래처",
                ),
                spacing="2",
                flex_wrap="wrap",
                align="center",
            ),
            rx.cond(
                DriverState.recent_collection_count > 0,
                rx.foreach(
                    DriverState.recent_collections,
                    lambda c: rx.hstack(
                        rx.text(c["collect_date"], font_size="11px", color="#6b7280", width="72px"),
                        rx.text(c["school_name"], font_size="13px", flex="1"),
                        rx.badge(c["item_type"], size="1"),
                        rx.text(
                            c["weight"].to(str) + "kg",
                            font_size="13px",
                            font_weight="600",
                        ),
                        rx.cond(
                            c["status"] == "draft",
                            rx.badge("📋임시", color_scheme="gray", variant="outline", size="1"),
                            rx.badge("✅전송", color_scheme="green", size="1"),
                        ),
                        rx.icon_button(
                            rx.icon("trash_2", size=14),
                            size="1",
                            variant="ghost",
                            color_scheme="red",
                            on_click=DriverState.delete_collection_entry(c["id"]),
                            disabled=~AuthState.is_user_active,
                        ),
                        width="100%",
                        padding_y="4px",
                        border_bottom="1px solid #f1f5f9",
                        align="center",
                    ),
                ),
                rx.text(
                    "조회 기간 내 수거 기록 없음",
                    font_size="13px",
                    color="#9ca3af",
                    text_align="center",
                    padding_y="8px",
                ),
            ),
            spacing="2",
            width="100%",
                ),  # rx.vstack (본문)
                rx.fragment(),
            ),  # rx.cond(recent_expanded)
        ),

        # ── 음성인식 결과 표시 ──
        rx.cond(
            DriverState.voice_result != "",
            rx.text(DriverState.voice_result, font_size="12px", color="#7c3aed"),
        ),

        spacing="3",
        width="100%",
        bg="white",
        border_radius="12px",
        padding="16px",
        box_shadow="0 2px 8px rgba(0,0,0,0.06)",
    )


def _processing_section() -> rx.Component:
    """계근표(처리확인) 섹션"""
    return rx.vstack(
        rx.hstack(
            rx.icon("scale", size=20, color="#1a73e8"),
            rx.text("처리확인 (계근표)", font_weight="700", font_size="16px"),
            rx.spacer(),
            rx.cond(
                DriverState.today_proc_count > 0,
                rx.badge(
                    "오늘 " + DriverState.today_proc_count.to(str) + "건",
                    color_scheme="blue",
                    size="1",
                ),
            ),
            rx.icon_button(
                rx.cond(
                    DriverState.weighslip_expanded,
                    rx.icon("chevron_up", size=14),
                    rx.icon("chevron_down", size=14),
                ),
                on_click=DriverState.toggle_weighslip_expanded,
                size="1",
                variant="ghost",
                color_scheme="gray",
                cursor="pointer",
            ),
            align="center",
        ),
        rx.cond(
            DriverState.weighslip_expanded,
            rx.vstack(
            rx.text(
            "처리장 도착 후 계근표 처리량을 입력하세요.",
            font_size="12px",
            color="#64748b",
        ),

        # ── 계량표 사진 OCR ──
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("scan", size=15, color="#7c3aed"),
                    rx.text("계량표 사진 OCR 자동입력", font_size="13px",
                            font_weight="600", color="#7c3aed"),
                    spacing="2", align="center",
                ),
                # Step 1: 파일 선택
                rx.upload(
                    rx.button(
                        rx.icon("camera", size=16),
                        "📷 사진 선택/촬영 (JPG/PNG)",
                        size="2",
                        variant="soft",
                        color_scheme="violet",
                        width="100%",
                    ),
                    id="weighslip_upload",
                    accept={"image/*": [".jpg", ".jpeg", ".png"]},
                    max_files=1,
                    multiple=False,
                    border="2px dashed #c4b5fd",
                    border_radius="8px",
                    padding="8px",
                    width="100%",
                ),
                rx.foreach(
                    rx.selected_files("weighslip_upload"),
                    lambda f: rx.text(
                        rx.icon("file-image", size=12),
                        " ", f,
                        font_size="11px", color="#7c3aed",
                    ),
                ),
                rx.button(
                    rx.icon("image", size=14),
                    "사진 등록",
                    on_click=DriverState.register_weighslip_image(
                        rx.upload_files(upload_id="weighslip_upload")
                    ),
                    size="2",
                    color_scheme="blue",
                    width="100%",
                ),
                # Step 2: 등록 완료 후 썸네일 + OCR 버튼
                rx.cond(
                    DriverState.weighslip_image_ready,
                    rx.vstack(
                        rx.image(
                            src=DriverState.weighslip_preview_data_url,
                            width="100%",
                            max_width="400px",
                            border_radius="8px",
                            border="1px solid #e5e7eb",
                            object_fit="contain",
                        ),
                        rx.button(
                            rx.icon("scan", size=14),
                            "OCR 자동 인식",
                            on_click=DriverState.run_weighslip_ocr,
                            loading=DriverState.weighslip_ocr_loading,
                            disabled=DriverState.weighslip_ocr_loading,
                            size="2",
                            color_scheme="green",
                            width="100%",
                        ),
                        spacing="2", width="100%",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    DriverState.weighslip_ocr_error != "",
                    rx.callout(
                        DriverState.weighslip_ocr_error,
                        color="red", size="1",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    DriverState.weighslip_ocr_done,
                    rx.vstack(
                        rx.divider(),
                        rx.text("📋 OCR 인식 결과 (수정 가능)",
                                font_size="12px", font_weight="600", color="#374151"),
                        rx.grid(
                            rx.vstack(
                                rx.text("1차 계근시간", font_size="11px", color="#64748b"),
                                rx.input(
                                    value=DriverState.weighslip_ocr_first_time,
                                    on_change=DriverState.set_weighslip_ocr_first_time,
                                    placeholder="예: 2026-04-08 14:05",
                                    size="2", width="100%",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("2차 계근시간", font_size="11px", color="#64748b"),
                                rx.input(
                                    value=DriverState.weighslip_ocr_second_time,
                                    on_change=DriverState.set_weighslip_ocr_second_time,
                                    placeholder="예: 2026-04-08 14:23",
                                    size="2", width="100%",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("차량번호", font_size="11px", color="#64748b"),
                                rx.input(
                                    value=DriverState.weighslip_ocr_vehicle_number,
                                    on_change=DriverState.set_weighslip_ocr_vehicle_number,
                                    placeholder="예: 12가3456",
                                    size="2", width="100%",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("총중량 (kg)", font_size="11px", color="#64748b"),
                                rx.input(
                                    value=DriverState.weighslip_ocr_gross_weight,
                                    on_change=DriverState.set_weighslip_ocr_gross_weight,
                                    placeholder="예: 7520",
                                    type="number", size="2", width="100%",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("실중량 (kg)", font_size="11px", color="#64748b"),
                                rx.input(
                                    value=DriverState.weighslip_ocr_net_weight,
                                    on_change=DriverState.set_weighslip_ocr_net_weight,
                                    placeholder="예: 3240",
                                    type="number", size="2", width="100%",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("처분업체", font_size="11px", color="#64748b"),
                                rx.input(
                                    value=DriverState.weighslip_ocr_company,
                                    on_change=DriverState.set_weighslip_ocr_company,
                                    placeholder="처분업체명",
                                    size="2", width="100%",
                                ),
                                spacing="1",
                                grid_column="1 / -1",
                            ),
                            columns="2",
                            spacing="2",
                            width="100%",
                        ),
                        rx.callout(
                            "실중량이 처리량에 자동 반영됩니다. 아래 폼에서 수정 후 전송하세요.",
                            color="violet", size="1",
                        ),
                        spacing="2", width="100%",
                    ),
                    rx.fragment(),
                ),
                spacing="2", width="100%",
            ),
            bg="#faf5ff",
            border="1px solid #e9d5ff",
            border_radius="8px",
            padding="12px",
            width="100%",
        ),

        # ── 처리량 + 처리장명 ──
        rx.hstack(
            rx.vstack(
                rx.text("처리량 (kg)", font_size="13px", font_weight="600", color="#374151"),
                rx.input(
                    placeholder="예: 500",
                    value=DriverState.proc_weight,
                    on_change=DriverState.set_proc_weight,
                    type="number",
                    input_mode="decimal",
                    width="100%",
                    size="3",
                ),
                spacing="1",
                flex="1",
            ),
            rx.vstack(
                rx.text("처리장명", font_size="13px", font_weight="600", color="#374151"),
                rx.input(
                    placeholder="예: ○○자원순환센터",
                    value=DriverState.proc_location,
                    on_change=DriverState.set_proc_location,
                    width="100%",
                    size="3",
                ),
                spacing="1",
                flex="1",
            ),
            width="100%",
            spacing="3",
        ),

        # ── 메모 ──
        rx.text("메모 (선택)", font_size="13px", font_weight="600", color="#374151"),
        rx.input(
            placeholder="특이사항",
            value=DriverState.proc_memo,
            on_change=DriverState.set_proc_memo,
            width="100%",
            size="3",
        ),

        # ── 전송 버튼 ──
        rx.button(
            "📤 처리확인 전송",
            on_click=DriverState.save_processing,
            disabled=~AuthState.is_user_active,
            width="100%",
            size="3",
            color_scheme="blue",
        ),

        # ── 메시지 ──
        rx.cond(
            DriverState.proc_save_msg != "",
            rx.text(
                DriverState.proc_save_msg,
                font_size="13px",
                color=rx.cond(
                    DriverState.proc_save_msg.contains("완료"),
                    "#16a34a",
                    "#dc2626",
                ),
            ),
        ),

        # ── 오늘 처리 이력 ──
        rx.cond(
            DriverState.today_proc_count > 0,
            rx.vstack(
                rx.text("오늘 처리확인 이력", font_size="13px", font_weight="600", color="#374151"),
                rx.foreach(
                    DriverState.today_processing,
                    lambda p: rx.hstack(
                        rx.text(p["confirm_time"], font_size="13px", color="#64748b"),
                        rx.text(p["location_name"], font_size="13px", flex="1"),
                        rx.text(
                            p["total_weight"].to(str) + "kg",
                            font_size="13px",
                            font_weight="600",
                        ),
                        rx.badge("📤전송", color_scheme="blue", size="1"),
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
            ),  # rx.vstack (본문)
            rx.fragment(),
        ),  # rx.cond(weighslip_expanded)

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
                    on_click=DriverState.open_checkout_dialog,
                    disabled=~AuthState.is_user_active,
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


def _floating_voice_button() -> rx.Component:
    """플로팅 음성 입력 버튼 — 화면 우측 상단 고정 (섹션 3)
    - 다이얼로그가 열려 있으면 숨김
    - 인식 중에는 tomato 색상 + spinner
    - 실시간 interim 텍스트를 버튼 왼쪽 말풍선으로 표시
    """
    return rx.cond(
        ~DriverState.voice_confirm_open,
        rx.box(
            rx.button(
                rx.cond(
                    DriverState.voice_active,
                    rx.spinner(size="3"),
                    rx.icon("mic", size=24),
                ),
                on_click=DriverState.start_global_voice,
                disabled=DriverState.voice_active,
                border_radius="50%",
                color_scheme=rx.cond(DriverState.voice_active, "tomato", "grass"),
                style={
                    "width": "56px",
                    "height": "56px",
                    "padding": "0",
                    "box_shadow": "0 4px 16px rgba(0,0,0,0.25)",
                },
            ),
            # 섹션 5: 실시간 interim 말풍선 (JS DOM 직접 업데이트)
            rx.cond(
                DriverState.voice_active,
                rx.box(
                    rx.html(
                        "<span id='voice-interim-text' style='color:#7c3aed;font-size:12px;"
                        "font-style:italic;'></span>"
                    ),
                    position="absolute",
                    right="64px",
                    top="10px",
                    background="white",
                    border_radius="8px",
                    padding="4px 10px",
                    box_shadow="0 2px 8px rgba(0,0,0,0.12)",
                    white_space="nowrap",
                    max_width="220px",
                ),
                rx.fragment(),
            ),
            position="fixed",
            top="16px",
            right="16px",
            z_index="1000",
        ),
    )


def _checkout_dialog() -> rx.Component:
    """퇴근 전 차량점검 다이얼로그"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                "🚗 퇴근 전 차량 점검",
                font_size="18px",
                font_weight="700",
            ),
            rx.text(
                "모든 항목을 확인하시고 체크해 주세요",
                font_size="13px",
                color="#64748b",
                margin_bottom="12px",
            ),
            rx.divider(),
            # ── 10개 항목 체크박스 ──
            rx.vstack(
                rx.foreach(
                    DriverState.vehicle_check_items,
                    lambda item, idx: rx.hstack(
                        rx.checkbox(
                            checked=item["checked"],
                            on_change=lambda _: DriverState.toggle_vehicle_check(idx),
                            size="3",
                            color_scheme="green",
                        ),
                        rx.text(
                            item["label"],
                            font_size="14px",
                            color=rx.cond(item["checked"], "#16a34a", "#374151"),
                            font_weight=rx.cond(item["checked"], "600", "400"),
                        ),
                        align="center",
                        spacing="3",
                        width="100%",
                        padding_y="6px",
                        border_bottom="1px solid #f1f5f9",
                    ),
                ),
                spacing="0",
                width="100%",
                margin_y="8px",
            ),
            rx.divider(),
            # ── 특이사항 입력 ──
            rx.vstack(
                rx.text(
                    "특이사항",
                    font_size="13px",
                    font_weight="600",
                    color="#374151",
                ),
                rx.text_area(
                    placeholder="이상이 있거나 인계할 사항을 적어주세요 (선택)",
                    value=DriverState.vehicle_check_remark,
                    on_change=DriverState.set_vehicle_check_remark,
                    rows="3",
                    width="100%",
                    font_size="13px",
                    border_radius="8px",
                    border="1px solid #e2e8f0",
                ),
                spacing="2",
                width="100%",
                margin_top="12px",
            ),
            # ── 버튼 ──
            rx.hstack(
                rx.button(
                    "취소",
                    on_click=DriverState.cancel_checkout,
                    variant="soft",
                    color_scheme="gray",
                    size="3",
                    flex="1",
                ),
                rx.button(
                    "✅ 확인 후 퇴근",
                    on_click=DriverState.confirm_checkout,
                    color_scheme="green",
                    size="3",
                    flex="1",
                    disabled=~DriverState.all_vehicle_items_checked,
                ),
                spacing="3",
                margin_top="16px",
                width="100%",
            ),
            max_width="460px",
            width="95vw",
            padding="20px",
        ),
        open=DriverState.checkout_dialog_open,
        on_open_change=DriverState.cancel_checkout,
    )


def _wake_word_bar() -> rx.Component:
    """기사 화면 상단 웨이크워드 토글 바.
    JS가 isIOS 감지 후 wake-android-bar / wake-ios-notice 를 교체함.
    """
    return rx.vstack(
        # ── 안드로이드/데스크탑용 바 (iOS에서 JS가 숨김) ──
        rx.hstack(
            rx.icon("mic", color=rx.cond(DriverState.wake_enabled, "green", "gray"), size=16),
            rx.text(
                "웨이크워드: ", DriverState.wake_status_text,
                font_size="0.9em",
            ),
            rx.spacer(),
            rx.switch(
                checked=DriverState.wake_enabled,
                on_change=DriverState.toggle_wake_word,
                color_scheme="green",
            ),
            rx.text("'수거' 라고 말하면 자동 입력", font_size="0.75em", color="gray"),
            width="100%",
            id="wake-android-bar",
        ),
        # ── iOS 안내 (기본 숨김, JS가 isIOS 시 표시) ──
        rx.html(
            "<div id='wake-ios-notice' style='display:none;width:100%;"
            "background:#fff3e0;color:#5d4037;font-size:13px;padding:6px 10px;"
            "border-radius:6px;border:1px solid #ffb74d;'>"
            "\U0001f34e iPhone\uc740 \uc6e8\uc774\ud06c\uc6cc\ub4dc\ub97c \uc9c0\uc6d0\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. "
            "\uc6b0\uce21 \U0001f3a4 \ubc84\ud2bc\uc744 \ub208\ub7ec \uc74c\uc131 \uc785\ub825\ud558\uc138\uc694.</div>"
        ),
        # ── 개발자 디버그줄 (?debug=1 일 때만 JS가 표시) ──
        rx.html(
            "<div id='wake-debug-reflex' style='display:none;width:100%;"
            "background:#fffde7;color:#333;font-size:12px;font-family:monospace;"
            "padding:3px 8px;border-radius:4px;border:1px solid #ffe082;'></div>"
        ),
        spacing="1",
        padding="6px 12px",
        border="1px solid #ddd",
        border_radius="8px",
        width="100%",
        background="#fafafa",
    )


def _wake_settings_panel() -> rx.Component:
    """호출명령 사용자 정의 — 웨이크워드 ON 시에만 표시 (iOS에서 JS가 숨김)."""
    return rx.cond(
        DriverState.wake_enabled,
        rx.vstack(
            rx.hstack(
                rx.text("시작 명령:", font_size="0.85em", width="80px"),
                rx.input(
                    value=DriverState.wake_keywords_start,
                    on_change=DriverState.set_wake_keywords_start,
                    placeholder="수거,입력,기록,제로다",
                    width="60%",
                ),
            ),
            rx.hstack(
                rx.text("종료 명령:", font_size="0.85em", width="80px"),
                rx.input(
                    value=DriverState.wake_keywords_stop,
                    on_change=DriverState.set_wake_keywords_stop,
                    placeholder="완료,끝,종료",
                    width="60%",
                ),
            ),
            rx.button(
                "저장",
                on_click=DriverState.save_wake_settings,
                size="1",
                color_scheme="green",
            ),
            spacing="1",
            padding="6px 12px",
            background="#f5f5f5",
            border_radius="6px",
            width="100%",
        ),
    )


def driver_page() -> rx.Component:
    """기사 대시보드 메인 페이지"""
    return rx.box(
        rx.vstack(
            # ── 웨이크워드 (페이지 최상단) ──
            _wake_word_bar(),
            _wake_settings_panel(),

            # ── 웨이크워드 JS 인라인 주입 v4 (iOS 차단 + debug ?debug=1) ──
            rx.script("""
console.log("[WAKE] script loaded v4");
(function () {
  if (window.__zerodaWake) return;

  // ── iOS 감지 (iPhone/iPad/iPod + iPad desktop mode) ──
  var ua = navigator.userAgent;
  var isIOS = /iPhone|iPad|iPod/.test(ua) ||
              (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var isPWA = window.navigator.standalone === true;
  var isDebug = window.location.search.indexOf("debug=1") !== -1;
  console.log("[WAKE] isIOS=" + isIOS + " isPWA=" + isPWA + " isDebug=" + isDebug);

  // ── iOS면 UI 교체 후 종료 ──
  if (isIOS) {
    document.addEventListener("DOMContentLoaded", applyIOS);
    if (document.readyState !== "loading") applyIOS();
    function applyIOS() {
      var android = document.getElementById("wake-android-bar");
      var notice  = document.getElementById("wake-ios-notice");
      if (android) android.style.display = "none";
      if (notice)  notice.style.display  = "block";
    }
    // 더미 객체만 등록 (startWakeWord 호출 시 아무것도 안 함)
    window.__zerodaWake = { running: false };
    window.zerodaWake   = {
      start: function() { console.log("[WAKE] iOS — blocked"); },
      stop:  function() {},
    };
    return;   // 이하 안드로이드 코드 실행 안 함
  }

  // ── 안드로이드 / 데스크탑 ──
  window.__zerodaWake = {
    recognition: null,
    running: false,
    starting: false,
    wakeLock: null,
    lastFireAt: 0,
    keywords: {
      start:  ["\uC218\uAC70", "\uC218\uAC00", "\uC218\uCEE4", "\uC18C\uAC70",
               "\uC785\uB825", "\uAE30\uB85D", "\uC81C\uB85C\uB2E4"],
      stop:   ["\uC644\uB8CC", "\uB05D", "\uC885\uB8CC", "\uC624\uD504"],
      cancel: ["\uCDE8\uC18C"],
    },
  };
  var W = window.__zerodaWake;

  // ── 디버그 (?debug=1 일 때만) ──
  function ts() {
    var d = new Date();
    return d.getHours() + ":" +
      String(d.getMinutes()).padStart(2,"0") + ":" +
      String(d.getSeconds()).padStart(2,"0");
  }
  function getOrCreateBodyBar() {
    var el = document.getElementById("wake-body-bar");
    if (!el) {
      el = document.createElement("div");
      el.id = "wake-body-bar";
      el.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99999;"
        + "background:#ffeb3b;color:#000;font-size:14px;font-family:monospace;"
        + "padding:4px 10px;text-align:center;pointer-events:none;";
      document.body.appendChild(el);
    }
    return el;
  }
  function setDebug(state, text) {
    var icons = {
      "listen": "\uD83C\uDF99 \uB4E3\uB294 \uC911",
      "wait":   "\u23F8 \uB300\uAE30",
      "error":  "\u274C \uC5D0\uB7EC",
      "heard":  "\u2705 \uC778\uC2DD",
      "off":    "\u2014",
    };
    var msg = "[" + ts() + "] " + (icons[state] || state) + (text ? ": " + text : "");
    console.log("[WAKE] " + msg);
    if (!isDebug) return;
    getOrCreateBodyBar().textContent = msg;
    var r = document.getElementById("wake-debug-reflex");
    if (r) { r.textContent = msg; r.style.display = "block"; }
    document.title = "[WAKE " + state + "] zeroda";
  }

  function showToast(msg) {
    var el = document.getElementById("wake-toast");
    if (!el) return;
    el.textContent = msg; el.style.display = "block";
    clearTimeout(el.__t);
    el.__t = setTimeout(function() { el.style.display = "none"; }, 3000);
  }

  // ── Wake Lock ──
  async function acquireWakeLock() {
    try {
      if ("wakeLock" in navigator) {
        W.wakeLock = await navigator.wakeLock.request("screen");
        W.wakeLock.addEventListener("release", function() { W.wakeLock = null; });
      }
    } catch(e) {}
  }
  function releaseWakeLock() {
    if (W.wakeLock) { try { W.wakeLock.release(); } catch(e) {} W.wakeLock = null; }
  }

  // ── 키워드 매칭 ──
  function matchKeyword(text, list) {
    var t = (text || "").split(" ").join("");
    return list.some(function(k) { return t.indexOf(k) !== -1; });
  }

  // ── safeStart: abort 후 재시작 ──
  function safeStart() {
    if (!W.running || W.starting) return;
    if (W.recognition) {
      try { W.recognition.abort(); } catch(e) {}
      W.recognition = null;
    }
    W.starting = true;
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      console.warn("[WAKE] SpeechRecognition not supported");
      setDebug("error", "not supported");
      W.running = false; W.starting = false; return;
    }
    var r = new SR();
    r.lang = "ko-KR";
    r.continuous = false;       // iOS: continuous 무조건 false
    r.interimResults = false;
    r.maxAlternatives = 3;      // 여러 후보 받아서 매칭률 향상

    r.onaudiostart = function() { console.log("[WAKE] onaudiostart"); };
    r.onsoundstart = function() { console.log("[WAKE] onsoundstart"); };
    r.onspeechstart = function() { console.log("[WAKE] onspeechstart"); setDebug("listen", "\uC74C\uC131 \uAC10\uC9C0\uB428"); };

    r.onstart = function() {
      W.starting = false;
      setDebug("listen", "");
      console.log("[WAKE] onstart — listening");
    };

    r.onresult = function(e) {
      console.log("[WAKE] onresult fired, results.length=" + e.results.length);
      var txt = "";
      if (e.results && e.results[0]) {
        for (var i = 0; i < e.results[0].length; i++) {
          txt += e.results[0][i].transcript + " ";
        }
      }
      txt = txt.trim();

      var startMatch  = matchKeyword(txt, W.keywords.start);
      var stopMatch   = matchKeyword(txt, W.keywords.stop);
      var cancelMatch = matchKeyword(txt, W.keywords.cancel);
      var label = startMatch ? "(\uC2DC\uC791\u2705)" : stopMatch ? "(\uC885\uB8CC\u2705)" : cancelMatch ? "(\uCDE8\uC18C\u2705)" : "(\uBB34\uC77C\uCE58\u274C)";
      setDebug("heard", "\u201C" + txt + "\u201D " + label);

      var now = Date.now();
      if (now - W.lastFireAt < 1500) return;

      if (stopMatch) {
        W.lastFireAt = now;
        stopWakeWord();
        showToast("\uD83C\uDF99 \uC74C\uC131 \uC785\uB825 \uC885\uB8CC");
        return;
      }
      if (cancelMatch) {
        W.lastFireAt = now;
        window.dispatchEvent(new CustomEvent("zeroda-wake-cancel"));
        return;
      }
      if (startMatch) {
        W.lastFireAt = now;
        showToast("\uD83C\uDF99 \uD638\uCD9C \uAC10\uC9C0!");
        window.dispatchEvent(new CustomEvent("zeroda-wake"));
        return;
      }
    };

    r.onerror = function(e) {
      W.starting = false;
      console.log("[WAKE] onerror: " + e.error);
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        setDebug("error", "\uAD8C\uD55C \uAC70\uBD80");
        W.running = false; return;
      }
      setDebug("error", e.error);
      if (W.running) setTimeout(safeStart, 400);
    };

    r.onend = function() {
      W.starting = false;
      console.log("[WAKE] onend, running=" + W.running);
      if (W.running) {
        setDebug("wait", "");
        setTimeout(safeStart, 200);
      } else {
        setDebug("off", "");
      }
    };

    try {
      r.start();
      W.recognition = r;
    } catch(e) {
      W.starting = false;
      console.warn("[WAKE] start threw:", e);
      if (W.running) setTimeout(safeStart, 800);
    }
  }

  // ── Public: startWakeWord ──
  async function startWakeWord() {
    if (W.running) return;

    // PWA(홈화면) 경고
    if (isIOS && isPWA) {
      showToast("\u26A0\uFE0F \uD648\uD654\uBA74 \uC571\uC5D0\uC11C\uB294 \uB9C8\uC774\uD06C\uAC00 \uCC28\uB2E8\uB420 \uC218 \uC788\uC2B5\uB2C8\uB2E4. Safari\uB85C \uC5F4\uC5B4\uC8FC\uC138\uC694.");
      console.warn("[WAKE] PWA mode on iOS — mic may be blocked");
    }

    // iOS: getUserMedia 명시 호출로 권한 트리거
    try {
      var stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(function(t) { t.stop(); });
    } catch(e) {
      console.warn("[WAKE] getUserMedia failed:", e);
      setDebug("error", "\uB9C8\uC774\uD06C \uAD8C\uD55C \uAC70\uBD80");
      showToast("\u274C \uB9C8\uC774\uD06C \uAD8C\uD55C\uC744 \uD5C8\uC6A9\uD574\uC8FC\uC138\uC694");
      return;
    }

    W.running = true;
    await acquireWakeLock();
    showToast("\uD83C\uDFA7 \uC6E8\uC774\uD06C\uC6CC\uB4DC ON — '\uC218\uAC70' \uB77C\uACE0 \uB9D0\uD558\uC138\uC694");
    safeStart();
  }

  function stopWakeWord() {
    W.running = false;
    if (W.recognition) { try { W.recognition.abort(); } catch(e) {} W.recognition = null; }
    releaseWakeLock();
    setDebug("off", "");
  }

  window.zerodaWake = { start: startWakeWord, stop: stopWakeWord };

  // 화면 숨김 시 자동 정지
  document.addEventListener("visibilitychange", function() {
    if (document.visibilityState === "hidden" && W.running) stopWakeWord();
  });
})();
"""),
            rx.script(
                "window.addEventListener('zeroda-wake-relay', function(){"
                "  var btn = document.getElementById('wake-trigger-btn');"
                "  if (btn) btn.click();"
                "});"
                "window.addEventListener('zeroda-wake-cancel', function(){"
                "  var btn = document.getElementById('wake-cancel-btn');"
                "  if (btn) btn.click();"
                "});"
            ),

            # 숨김 트리거 버튼 (JS 이벤트 → Reflex state 브릿지)
            rx.button(
                "wake-trigger",
                id="wake-trigger-btn",
                on_click=DriverState.on_wake_triggered,
                display="none",
            ),
            rx.button(
                "wake-cancel",
                id="wake-cancel-btn",
                on_click=DriverState.on_wake_cancel,
                display="none",
            ),

            # 토스트 (별도 rx.html)
            rx.html(
                "<div id='wake-toast' style='position:fixed;top:60px;left:50%;"
                "transform:translateX(-50%);background:#333;color:#fff;"
                "padding:8px 16px;border-radius:8px;display:none;z-index:9999;font-size:15px;'></div>"
            ),

            # manifest 링크
            rx.html("<link rel='manifest' href='/manifest.webmanifest'>"),

            rx.cond(
                ~AuthState.is_user_active,
                rx.callout(
                    "본사 관리자 활성화 대기 중입니다. 활성화 전까지 기능 사용이 제한됩니다.",
                    icon="info",
                    color_scheme="amber",
                    size="2",
                    margin_bottom="12px",
                ),
                rx.fragment(),
            ),
            _header(),
            _weather_section(),
            _schoolzone_section(),
            _safety_section(),
            _schedule_section(),
            _voice_confirm_dialog(),
            _voice_pick_dialog(),
            _floating_voice_button(),
            _processing_section(),
            _checkout_section(),
            _checkout_dialog(),

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
            on_mount=DriverState.load_wake_settings,
        ),
        bg="#f1f5f9",
        min_height="100vh",
    )
