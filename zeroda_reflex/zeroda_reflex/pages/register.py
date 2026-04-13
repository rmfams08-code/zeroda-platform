# zeroda_reflex/pages/register.py
# 회원가입 페이지 — 2026-04-08 복구본
# 기존 파일이 143줄에서 미완 상태로 잘림 → 전체 재작성
import reflex as rx
from zeroda_reflex.state.auth_state import AuthState


def register_page() -> rx.Component:
    role_options = [
        {"value": "driver", "label": "기사"},
        {"value": "vendor_admin", "label": "업체관리자"},
        {"value": "school", "label": "학교"},
        {"value": "edu_office", "label": "교육청"},
        {"value": "meal_manager", "label": "급식담당자"},
    ]

    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("ZERODA 회원가입", size="6", text_align="center"),
                rx.text(
                    "본사 관리자 승인 후 로그인이 가능합니다.",
                    color="gray", size="2", text_align="center",
                ),
                rx.divider(),

                # 아이디
                rx.vstack(
                    rx.text("아이디 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                    rx.input(
                        placeholder="아이디 (영문/숫자)",
                        value=AuthState.reg_id,
                        on_change=AuthState.set_reg_id,
                        auto_complete="off",
                        name="reg_user_id",
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),

                # 이름
                rx.vstack(
                    rx.text("이름 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                    rx.input(
                        placeholder="실명",
                        value=AuthState.reg_name,
                        on_change=AuthState.set_reg_name,
                        auto_complete="off",
                        name="reg_full_name",
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),

                # 비밀번호
                rx.vstack(
                    rx.text("비밀번호 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                    rx.box(
                        rx.input(
                            placeholder="최소 8자, 대·소문자+숫자+특수문자 포함",
                            type=rx.cond(AuthState.show_reg_pw, "text", "password"),
                            value=AuthState.reg_pw,
                            on_change=AuthState.set_reg_pw,
                            auto_complete="new-password",
                            name="reg_new_pw",
                            width="100%",
                        ),
                        rx.box(
                            rx.icon(
                                rx.cond(AuthState.show_reg_pw, "eye_off", "eye"),
                                size=16, color="#94a3b8", cursor="pointer",
                                on_click=AuthState.toggle_reg_pw,
                            ),
                            position="absolute", right="10px", top="50%",
                            transform="translateY(-50%)",
                        ),
                        position="relative", width="100%",
                    ),
                    # 비밀번호 강도 바
                    rx.cond(
                        AuthState.reg_pw != "",
                        rx.vstack(
                            rx.hstack(
                                rx.box(
                                    width=rx.cond(
                                        AuthState.pw_strength >= 1, "100%", "0%"
                                    ),
                                    height="4px",
                                    bg=AuthState.pw_strength_color,
                                    border_radius="2px",
                                    transition="all 0.3s ease",
                                    flex="1",
                                ),
                                rx.box(
                                    width=rx.cond(
                                        AuthState.pw_strength >= 2, "100%", "0%"
                                    ),
                                    height="4px",
                                    bg=rx.cond(
                                        AuthState.pw_strength >= 2,
                                        AuthState.pw_strength_color,
                                        "#e2e8f0",
                                    ),
                                    border_radius="2px",
                                    transition="all 0.3s ease",
                                    flex="1",
                                ),
                                rx.box(
                                    width=rx.cond(
                                        AuthState.pw_strength >= 3, "100%", "0%"
                                    ),
                                    height="4px",
                                    bg=rx.cond(
                                        AuthState.pw_strength >= 3,
                                        AuthState.pw_strength_color,
                                        "#e2e8f0",
                                    ),
                                    border_radius="2px",
                                    transition="all 0.3s ease",
                                    flex="1",
                                ),
                                rx.box(
                                    width=rx.cond(
                                        AuthState.pw_strength >= 4, "100%", "0%"
                                    ),
                                    height="4px",
                                    bg=rx.cond(
                                        AuthState.pw_strength >= 4,
                                        AuthState.pw_strength_color,
                                        "#e2e8f0",
                                    ),
                                    border_radius="2px",
                                    transition="all 0.3s ease",
                                    flex="1",
                                ),
                                spacing="1", width="100%",
                            ),
                            rx.text(
                                AuthState.pw_strength_label,
                                size="1",
                                color=AuthState.pw_strength_color,
                                font_weight="600",
                            ),
                            spacing="1", width="100%",
                        ),
                        rx.fragment(),
                    ),
                    rx.text(
                        "8자 이상 · 대문자 · 소문자 · 숫자 · 특수문자(!@#$%^&* 등) 각 1자 이상",
                        size="1",
                        color="gray",
                    ),
                    spacing="1", width="100%",
                ),

                # 비밀번호 확인
                rx.vstack(
                    rx.text("비밀번호 확인 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                    rx.box(
                        rx.input(
                            placeholder="비밀번호 재입력",
                            type=rx.cond(AuthState.show_reg_pw2, "text", "password"),
                            value=AuthState.reg_pw2,
                            on_change=AuthState.set_reg_pw2,
                            auto_complete="new-password",
                            name="reg_confirm_pw",
                            width="100%",
                        ),
                        rx.box(
                            rx.icon(
                                rx.cond(AuthState.show_reg_pw2, "eye_off", "eye"),
                                size=16, color="#94a3b8", cursor="pointer",
                                on_click=AuthState.toggle_reg_pw2,
                            ),
                            position="absolute", right="10px", top="50%",
                            transform="translateY(-50%)",
                        ),
                        position="relative", width="100%",
                    ),
                    # 비밀번호 불일치 경고
                    rx.cond(
                        (AuthState.reg_pw2 != "") & (AuthState.reg_pw != AuthState.reg_pw2),
                        rx.text("비밀번호가 일치하지 않습니다", size="1", color="#ef4444"),
                        rx.fragment(),
                    ),
                    spacing="1", width="100%",
                ),

                # 역할 선택
                rx.vstack(
                    rx.text("역할 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                    rx.radio_group(
                        [item["value"] for item in role_options],
                        value=AuthState.reg_role,
                        on_change=AuthState.set_reg_role,
                        direction="row",
                        spacing="3",
                    ),
                    spacing="1", width="100%",
                ),

                # 업체 선택 (driver, vendor_admin)
                rx.cond(
                    (AuthState.reg_role == "driver")
                    | (AuthState.reg_role == "vendor_admin"),
                    rx.vstack(
                        # driver: 기존 업체 드롭다운만
                        rx.cond(
                            AuthState.reg_role == "driver",
                            rx.vstack(
                                rx.text("소속 업체 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                                rx.select(
                                    AuthState.reg_vendor_options,
                                    value=AuthState.reg_vendor,
                                    on_change=AuthState.set_reg_vendor,
                                    placeholder="업체를 선택하세요",
                                    width="100%",
                                ),
                                rx.callout(
                                    "기사는 이미 등록된 업체에만 소속 가능합니다.",
                                    color_scheme="blue",
                                    size="1",
                                    width="100%",
                                ),
                                spacing="2", width="100%",
                            ),
                            rx.fragment(),
                        ),
                        # vendor_admin: 기존/신규 선택
                        rx.cond(
                            AuthState.reg_role == "vendor_admin",
                            rx.vstack(
                                rx.text("업체 유형 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                                rx.radio_group(
                                    ["기존 업체 소속", "새 업체 등록"],
                                    value=AuthState.reg_vendor_mode,
                                    on_change=AuthState.set_reg_vendor_mode,
                                    direction="row",
                                    spacing="4",
                                ),
                                rx.cond(
                                    AuthState.reg_vendor_mode == "기존 업체 소속",
                                    rx.vstack(
                                        rx.text("소속 업체 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                                        rx.select(
                                            AuthState.reg_vendor_options,
                                            value=AuthState.reg_vendor,
                                            on_change=AuthState.set_reg_vendor,
                                            placeholder="업체를 선택하세요",
                                            width="100%",
                                        ),
                                        spacing="2", width="100%",
                                    ),
                                    rx.fragment(),
                                ),
                                rx.cond(
                                    AuthState.reg_vendor_mode == "새 업체 등록",
                                    rx.vstack(
                                        rx.text("업체명 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                                        rx.input(
                                            placeholder="새 업체명",
                                            value=AuthState.reg_new_vendor_name,
                                            on_change=AuthState.set_reg_new_vendor_name,
                                            width="100%",
                                        ),
                                        rx.text("사업자등록번호", size="2", weight="bold"),
                                        rx.input(
                                            placeholder="000-00-00000",
                                            value=AuthState.reg_new_biz_no,
                                            on_change=AuthState.set_reg_new_biz_no,
                                            width="100%",
                                        ),
                                        rx.text("대표자명", size="2", weight="bold"),
                                        rx.input(
                                            placeholder="대표자 성명",
                                            value=AuthState.reg_new_rep,
                                            on_change=AuthState.set_reg_new_rep,
                                            width="100%",
                                        ),
                                        rx.text("주소", size="2", weight="bold"),
                                        rx.input(
                                            placeholder="사업장 주소",
                                            value=AuthState.reg_new_address,
                                            on_change=AuthState.set_reg_new_address,
                                            width="100%",
                                        ),
                                        rx.text("연락처", size="2", weight="bold"),
                                        rx.input(
                                            placeholder="대표 연락처",
                                            value=AuthState.reg_new_contact,
                                            on_change=AuthState.set_reg_new_contact,
                                            width="100%",
                                        ),
                                        rx.callout(
                                            "새 업체 정보는 본사 관리자 승인 후 등록됩니다.",
                                            color_scheme="amber",
                                            size="1",
                                            width="100%",
                                        ),
                                        spacing="2", width="100%",
                                    ),
                                    rx.fragment(),
                                ),
                                spacing="2", width="100%",
                            ),
                            rx.fragment(),
                        ),
                        spacing="2", width="100%",
                    ),
                    rx.fragment(),
                ),

                # 학교/급식담당자 전용 (NEIS 연동)
                rx.cond(
                    (AuthState.reg_role == "school")
                    | (AuthState.reg_role == "meal_manager"),
                    rx.vstack(
                        rx.text("소속 업체 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                        rx.select(
                            AuthState.reg_vendor_options,
                            value=AuthState.reg_vendor_select,
                            on_change=AuthState.set_reg_vendor_select,
                            placeholder="업체를 선택하세요",
                            width="100%",
                        ),
                        rx.text("학교명 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                        rx.input(
                            placeholder="학교 정식 명칭 (NEIS 등록명)",
                            value=AuthState.reg_school_name_neis,
                            on_change=AuthState.set_reg_school_name_neis,
                            width="100%",
                        ),
                        rx.text("NEIS 교육청코드 (선택, 7자리)", size="2", weight="bold"),
                        rx.input(
                            placeholder="(선택) 7자리 숫자 — 추후 관리자가 등록 가능",
                            value=AuthState.reg_neis_edu,
                            on_change=AuthState.set_reg_neis_edu,
                            max_length=7,
                            width="100%",
                        ),
                        rx.text("NEIS 학교코드 (선택, 7자리)", size="2", weight="bold"),
                        rx.input(
                            placeholder="(선택) 7자리 숫자 — 추후 관리자가 등록 가능",
                            value=AuthState.reg_neis_school,
                            on_change=AuthState.set_reg_neis_school,
                            max_length=7,
                            width="100%",
                        ),
                        rx.callout(
                            "NEIS 코드는 선택사항입니다. 나이스 학교정보 사이트에서 확인할 수 있으며, 모르는 경우 본사 관리자가 승인 후 등록해 드립니다.",
                            color_scheme="blue",
                            size="1",
                            width="100%",
                        ),
                        spacing="2", width="100%",
                    ),
                    rx.fragment(),
                ),

                # 교육청 (edu_office)
                rx.cond(
                    AuthState.reg_role == "edu_office",
                    rx.vstack(
                        rx.text("교육청 ", rx.text("*", color="#ef4444", as_="span"), size="2", weight="bold"),
                        rx.input(
                            placeholder="소속 교육청명",
                            value=AuthState.reg_edu_office,
                            on_change=AuthState.set_reg_edu_office,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                    rx.fragment(),
                ),

                rx.divider(),

                # 에러 / 성공 메시지
                rx.cond(
                    AuthState.reg_error != "",
                    rx.callout(
                        AuthState.reg_error,
                        icon="triangle_alert",
                        color_scheme="red",
                        size="1",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    AuthState.reg_success != "",
                    rx.callout(
                        AuthState.reg_success,
                        icon="circle_check",
                        color_scheme="green",
                        size="1",
                        width="100%",
                    ),
                    rx.fragment(),
                ),

                # 가입 버튼
                rx.button(
                    rx.cond(AuthState.reg_loading, "처리 중...", "가입 신청"),
                    on_click=AuthState.submit_register,
                    disabled=AuthState.reg_loading,
                    size="3",
                    width="100%",
                    color_scheme="blue",
                ),

                # 로그인 페이지로
                rx.hstack(
                    rx.text("이미 계정이 있으신가요?", size="2", color="gray"),
                    rx.link("로그인", href="/", size="2", color_scheme="blue"),
                    spacing="2",
                    justify="center",
                    width="100%",
                ),

                spacing="3",
                width="100%",
            ),
            size="3",
            width="500px",
            max_width="95vw",
        ),
        width="100%",
        min_height="100vh",
        padding_y="6",
        on_mount=AuthState.load_signup_vendor_options,
    )
