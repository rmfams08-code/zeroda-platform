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


def _schedule_school_card(s: dict) -> rx.Component:
    """일정 학교 카드 (완료/미완료 표시 + 지도 링크)"""
    school_name = s["school_name"]
    items_text = s["items"]
    address = s["address"]
    is_done = DriverState.collected_schools.contains(school_name)
    return rx.vstack(
        rx.hstack(
            rx.cond(
                is_done,
                rx.icon("circle_check", color="#16a34a", size=16),
                rx.icon("circle", color="#d1d5db", size=16),
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(s["icon"], font_size="14px"),
                    rx.text(
                        school_name,
                        font_size="14px",
                        font_weight="600",
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
                rx.badge("완료", color_scheme="green", size="1"),
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
        width="100%",
        padding="10px 12px",
        bg=rx.cond(is_done, "#f0fdf4", "white"),
        border=rx.cond(is_done, "1px solid #bbf7d0", "1px solid #e5e7eb"),
        border_radius="8px",
        spacing="2",
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
                # 학교 카드 목록
                rx.foreach(
                    DriverState.schedule_schools,
                    _schedule_school_card,
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

        spacing="3",
        width="100%",
        bg="white",
        border_radius="12px",
        padding="16px",
        box_shadow="0 2px 8px rgba(0,0,0,0.06)",
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
        rx.hstack(
            rx.cond(
                DriverState.selected_school != "",
                rx.text(DriverState.selected_school_icon, font_size="15px"),
            ),
            rx.text("거래처", font_size="13px", font_weight="600", color="#374151"),
            spacing="1",
            align="center",
        ),
        rx.select(
            DriverState.assigned_schools,
            value=DriverState.selected_school,
            on_change=DriverState.set_selected_school,
            placeholder="거래처를 선택하세요",
            width="100%",
        ),

        # ── 음성입력 ──
        rx.hstack(
            rx.button(
                "🎤 음성으로 수거량 입력",
                size="1",
                variant="outline",
                color_scheme="purple",
                on_click=rx.call_script(
                    "new Promise((resolve) => {"
                    "  try {"
                    "    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;"
                    "    if (!SR) { resolve('지원안됨'); return; }"
                    "    const r = new SR();"
                    "    r.lang = 'ko-KR'; r.maxAlternatives = 1;"
                    "    r.onresult = (e) => resolve(e.results[0][0].transcript);"
                    "    r.onerror = () => resolve('');"
                    "    r.onend = () => {};"
                    "    r.start();"
                    "  } catch(e) { resolve('지원안됨'); }"
                    "})",
                    callback=DriverState.handle_voice_result,
                ),
            ),
            rx.cond(
                DriverState.voice_result != "",
                rx.text(DriverState.voice_result, font_size="11px", color="#7c3aed"),
            ),
            width="100%",
            spacing="2",
            align="center",
        ),

        # ── GPS 위치 저장 ──
        rx.hstack(
            rx.button(
                "📍 현재 위치 저장",
                size="1",
                variant="outline",
                on_click=rx.call_script(
                    "new Promise((resolve) => {"
                    "  navigator.geolocation.getCurrentPosition("
                    "    (pos) => resolve(pos.coords.latitude + ',' + pos.coords.longitude),"
                    "    () => resolve('0,0')"
                    "  );"
                    "})",
                    callback=DriverState.save_gps_location,
                ),
            ),
            rx.cond(
                DriverState.gps_msg != "",
                rx.text(DriverState.gps_msg, font_size="11px", color="#64748b"),
            ),
            width="100%",
            spacing="2",
            align="center",
        ),

        # ── 날짜별 다중행 수거입력 ──
        rx.hstack(
            rx.text("날짜별 수거량", font_size="13px", font_weight="600", color="#374151"),
            rx.spacer(),
            rx.button(
                "＋ 날짜 추가",
                on_click=DriverState.add_collection_row,
                size="1",
                variant="outline",
            ),
            width="100%",
        ),
        rx.foreach(
            DriverState.collection_rows,
            lambda row, idx: rx.hstack(
                rx.input(
                    value=row["date"],
                    on_change=lambda v: DriverState.set_row_date([idx, v]),
                    type="date",
                    size="2",
                    width="120px",
                ),
                rx.select(
                    ["음식물", "재활용", "일반"],
                    value=row["item"],
                    on_change=lambda v: DriverState.set_row_item([idx, v]),
                    size="2",
                    width="90px",
                ),
                rx.input(
                    placeholder="kg",
                    value=row["weight"],
                    on_change=lambda v: DriverState.set_row_weight([idx, v]),
                    type="number",
                    input_mode="decimal",
                    size="2",
                    flex="1",
                ),
                rx.cond(
                    idx > 0,
                    rx.icon_button(
                        rx.icon("trash_2", size=14),
                        size="1",
                        variant="ghost",
                        color_scheme="red",
                        on_click=DriverState.remove_collection_row(idx),
                    ),
                    rx.box(width="28px"),
                ),
                width="100%",
                spacing="2",
                align="center",
            ),
        ),

        # ── 단가 + 예상금액 ──
        rx.hstack(
            rx.vstack(
                rx.text("단가 (원/kg)", font_size="13px", font_weight="600", color="#374151"),
                rx.input(
                    placeholder="예: 120",
                    value=DriverState.collection_unit_price,
                    on_change=DriverState.set_collection_unit_price,
                    type="number",
                    input_mode="decimal",
                    width="100%",
                    size="3",
                ),
                spacing="1",
                flex="1",
            ),
            rx.vstack(
                rx.text("예상금액", font_size="13px", font_weight="600", color="#374151"),
                rx.box(
                    rx.text(
                        DriverState.estimated_amount,
                        font_size="16px",
                        font_weight="700",
                        color="#1a73e8",
                    ),
                    bg="#eff6ff",
                    border_radius="8px",
                    padding="8px 12px",
                    width="100%",
                    text_align="center",
                ),
                spacing="1",
                flex="1",
            ),
            width="100%",
            spacing="3",
        ),

        # ── 수거시간 ──
        rx.text("수거시간", font_size="13px", font_weight="600", color="#374151"),
        rx.input(
            value=DriverState.collection_time,
            on_change=DriverState.set_collection_time,
            type="time",
            width="100%",
            size="3",
        ),

        # ── 메모 ──
        rx.text("메모", font_size="13px", font_weight="600", color="#374151"),
        rx.text_area(
            placeholder="수거 관련 메모 (선택)",
            value=DriverState.collection_memo,
            on_change=DriverState.set_collection_memo,
            width="100%",
            rows="2",
        ),

        # ── 사진 촬영/첨부 (최대 3장) ──
        rx.text("수거 사진 (최대 3장)", font_size="13px", font_weight="600", color="#374151"),
        rx.upload(
            rx.button("📷 사진 선택/촬영", size="2", variant="outline", width="100%"),
            id="collection_photo",
            accept={"image/*": [".jpg", ".jpeg", ".png"]},
            max_files=3,
            multiple=True,
        ),
        rx.button(
            "📤 사진 업로드",
            on_click=DriverState.handle_photo_upload(rx.upload_files(upload_id="collection_photo")),
            size="2",
            variant="outline",
            width="100%",
        ),
        rx.cond(
            DriverState.photo_upload_msg != "",
            rx.text(
                DriverState.photo_upload_msg,
                font_size="12px",
                color=rx.cond(
                    DriverState.photo_upload_msg.contains("완료"), "#16a34a", "#dc2626",
                ),
            ),
        ),
        rx.cond(
            DriverState.today_photo_count > 0,
            rx.text(
                "오늘 사진 " + DriverState.today_photo_count.to(str) + "장 등록됨",
                font_size="12px",
                color="#64748b",
            ),
        ),

        # ── 저장 버튼 2개: 임시저장 / 수거완료 ──
        rx.hstack(
            rx.button(
                "📋 임시저장",
                on_click=DriverState.save_collection_draft,
                flex="1",
                size="3",
                variant="outline",
                color_scheme="gray",
            ),
            rx.button(
                "✅ 수거완료·본사전송",
                on_click=DriverState.save_collection_entry,
                flex="1",
                size="3",
                color_scheme="blue",
            ),
            width="100%",
            spacing="2",
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
        ),
        rx.text(
            "처리장 도착 후 계근표 처리량을 입력하세요.",
            font_size="12px",
            color="#64748b",
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
            _schoolzone_section(),
            _safety_section(),
            _schedule_section(),
            _collection_section(),
            _processing_section(),
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
