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
                    (AuthState.reg_role == "driver")
                    | (AuthState.reg_role == "vendor_admin"),
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
                    rx.fragment(),
                ),

                # 학교/급식담당자 전용 (NEIS 연동)
                rx.cond(
                    (AuthState.reg_role == "school")
                    | (AuthState.reg_role == "meal_manager"),
                    rx.vstack(
                        rx.text("소속 업체 *", size="2", weight="bold"),
                        rx.select(
                            AuthState.reg_vendor_options,
                            value=AuthState.reg_vendor_select,
                            on_change=AuthState.set_reg_vendor_select,
                            placeholder="업체를 선택하세요",
                            width="100%",
                        ),
                        rx.text("학교명 *", size="2", weight="bold"),
                        rx.input(
                            placeholder="학교 정식 명칭 (NEIS 등록명)",
                            value=AuthState.reg_school_name_neis,
                            on_change=AuthState.set_reg_school_name_neis,
                            width="100%",
                        ),
                        rx.text("NEIS 교육청코드 * (7자리)", size="2", weight="bold"),
                        rx.input(
                            placeholder="7자리 숫자",
                            value=AuthState.reg_neis_edu,
                            on_change=AuthState.set_reg_neis_edu,
                            max_length=7,
                            width="100%",
                        ),
                        rx.text("NEIS 학교코드 * (7자리)", size="2", weight="bold"),
                        rx.input(
                            placeholder="7자리 숫자",
                            value=AuthState.reg_neis_school,
                            on_change=AuthState.set_reg_neis_school,
                            max_length=7,
                            width="100%",
                        ),
                        rx.callout(
                            "NEIS 코드는 나이스 학교정보 사이트에서 확인할 수 있습니다. 승인 시 자동으로 거래처에 등록됩니다.",
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
                        rx.text("교육청 *", size="2", weight="bold"),
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
