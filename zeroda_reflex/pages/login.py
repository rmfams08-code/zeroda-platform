# zeroda_reflex/pages/login.py
# 로그인 페이지 — 기존 Streamlit 디자인 재현
import reflex as rx
from zeroda_reflex.state.auth_state import AuthState


def login_page() -> rx.Component:
    """로그인 페이지"""
    return rx.box(
        rx.center(
            rx.vstack(
                # ── 브랜드 로고 ──
                rx.hstack(
                    rx.box(
                        rx.text("Z", font_size="22px", font_weight="800", color="white"),
                        width="50px",
                        height="50px",
                        bg="linear-gradient(135deg, #38bd94, #3b82f6)",
                        border_radius="14px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        box_shadow="0 6px 20px rgba(56,189,148,0.35)",
                    ),
                    rx.vstack(
                        rx.text(
                            "ZERODA",
                            font_size="26px",
                            font_weight="800",
                            background="linear-gradient(135deg, #0f172a, #334155)",
                            background_clip="text",
                            color="transparent",
                            line_height="1.2",
                        ),
                        rx.text(
                            "Waste Data Platform",
                            font_size="11px",
                            font_weight="600",
                            color="#94a3b8",
                            letter_spacing="2.5px",
                        ),
                        spacing="0",
                    ),
                    spacing="3",
                    align="center",
                    margin_bottom="32px",
                ),

                # ── 로그인 타이틀 ──
                rx.text("로그인", font_size="24px", font_weight="700", color="#0f172a"),
                rx.text(
                    "계정 정보를 입력하여 접속하세요",
                    font_size="14px",
                    color="#64748b",
                    margin_bottom="20px",
                ),

                # ── 로그인 폼 (엔터키 제출 지원) ──
                rx.form(
                    rx.vstack(
                        rx.text("아이디", font_size="13px", font_weight="600", color="#1e293b"),
                        rx.input(
                            name="user_id",
                            placeholder="아이디를 입력하세요",
                            size="3",
                            width="100%",
                            border_radius="12px",
                        ),

                        rx.text(
                            "비밀번호",
                            font_size="13px",
                            font_weight="600",
                            color="#1e293b",
                            margin_top="8px",
                        ),
                        rx.input(
                            name="password",
                            type="password",
                            placeholder="비밀번호를 입력하세요",
                            size="3",
                            width="100%",
                            border_radius="12px",
                        ),

                        # ── 로그인 버튼 ──
                        rx.button(
                            rx.cond(
                                AuthState.login_loading,
                                rx.spinner(size="1"),
                                rx.text("로그인"),
                            ),
                            type="submit",
                            width="100%",
                            size="3",
                            bg="linear-gradient(135deg, #38bd94, #2da37e)",
                            color="white",
                            border_radius="12px",
                            margin_top="12px",
                            cursor="pointer",
                            _hover={"transform": "translateY(-2px)", "box_shadow": "0 8px 24px rgba(56,189,148,0.4)"},
                        ),

                        spacing="1",
                        width="100%",
                    ),
                    on_submit=AuthState.login,
                    width="100%",
                ),

                # ── 에러 메시지 ──
                rx.cond(
                    AuthState.login_error != "",
                    rx.callout(
                        AuthState.login_error,
                        icon="circle_alert",
                        color_scheme="red",
                        width="100%",
                        margin_top="8px",
                    ),
                ),

                # ── 하단 카피라이트 ──
                rx.text(
                    "\u00a9 2026 ZERODA \u00b7 하영자원 폐기물데이터플랫폼",
                    font_size="11px",
                    color="#94a3b8",
                    text_align="center",
                    margin_top="28px",
                ),

                # ── 카드 스타일 ──
                bg="white",
                border_radius="24px",
                padding="48px",
                box_shadow="0 20px 50px rgba(0,0,0,0.10), 0 4px 16px rgba(0,0,0,0.06)",
                border="1px solid rgba(226,232,240,0.6)",
                width=["90%", "90%", "450px"],
                spacing="1",
            ),
            min_height="100vh",
            padding_top="80px",
        ),
        # ── 배경 ──
        bg="linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 50%, #f8fafc 100%)",
        min_height="100vh",
    )
