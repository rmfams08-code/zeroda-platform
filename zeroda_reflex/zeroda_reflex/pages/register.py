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
                rx.text("본사 관리자 승인 후 로그인이 가능합니다.", color="gray", size="2", text_align="center"),
                rx.divider(),
                # 아이디
                rx.vstack(
                    rx.text("아이디 *", size="2", weight="bold"),
                    rx.input(
                        placeholder="아이디 (영문/숫자)",
                        value=AuthState.reg_id,
                        on_change=AuthState.set_reg_id,
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),
                # 이름
                rx.vstack(
                    rx.text("이름 *", size="2", weight="bold"),
                    rx.input(
                        placeholder="실명",
                        value=AuthState.reg_name,
                        on_change=AuthState.set_reg_name,
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),
                # 비밀번호
                rx.vstack(
                    rx.text("비밀번호 *", size="2", weight="bold"),
                    rx.input(
                        placeholder="최소 8자, 대문자+숫자+특수문자 포함",
                        type="password",
                        value=AuthState.reg_pw,
                        on_change=AuthState.set_reg_pw,
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),
                # 비밀번호 확인
                rx.vstack(
                    rx.text("비밀번호 확인 *", size="2", weight="bold"),
                    rx.input(
                        placeholder="비밀번호 재입력",
                        type="password",
                        value=AuthState.reg_pw2,
                        on_change=AuthState.set_reg_pw2,
                        width="100%",
                    ),
                    spacing="1", width="100%",
                ),
                # 역할 선택
                rx.vstack(
                    rx.text("역할 *", size="2", weight="bold"),
                    rx.radio_group(
                        [item["value"] for item in role_options],
                        value=AuthState.reg_role,
                        on_change=AuthState.set_reg_role,
                        direction="row",
                        spacing="3",
                    ),
                    spacing="1", width="100%",
                ),
                # 업체명 (driver, vendor_admin)
                rx.cond(
                    (AuthState.reg_role == "driver") | (AuthState.reg_role == "vendor_admin"),
                    rx.vstack(
                        rx.text("업체명", size="2", weight="bold"),
                        rx.input(
                            placeholder="소속 업체명",
                            value=AuthState.reg_vendor,
                            on_change=AuthState.set_reg_vendor,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                ),
                # 학교명 (school, meal_manager)
                rx.cond(
                    (AuthState.reg_role == "school") | (AuthState.reg_role == "meal_manager"),
                    rx.vstack(
                        rx.text("학교명", size="2", weight="bold"),
                        rx.input(
                            placeholder="소속 학교명",
                            value=AuthState.reg_schools,
                            on_change=AuthState.set_reg_schools,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                ),
                # 교육청 (edu_office)
                rx.cond(
                    AuthState.reg_role == "edu_office",
                    rx.vstack(
                        rx.text("교육청", size="2", weight="bold"),
                        rx.input(
                            placeholder="소속 교육청명",
                            value=AuthState.reg_edu_office,
                            on_change=AuthState.set_reg_edu_office,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                ),
                # 에러 메시지
                rx.cond(
                    AuthState.reg_error != "",
                    rx.callout(
                        AuthState.reg_error,
                        color_scheme="red",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                # 성공 메시지
                rx.cond(
                    AuthState.reg_success != "",
                    rx.callout(
                        AuthState.reg_success,
                        color_scheme="green",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                # 가입 버튼
                rx.button(
                    "가입 신청",
                    on_click=AuthState.submit_register,
                    loading=AuthState.reg_loading,
                    width="100%",
                    size="3",
                    color_scheme="blue",
                ),
                # 로그인으로 돌아가기
                rx.button(
                    "로그인으로 돌아가기",
                    on_click=AuthState.goto_login,
                    variant="outline",
                    width="100%",
                    size="2",
                ),
                spacing="4",
                width="100%",
            ),
            width="420px",
            padding="32px",
        ),
        min_height="100vh",
        background="var(--gray-2)",
    )
