# zeroda_reflex/zeroda_reflex/components/footer.py
import reflex as rx


def site_footer() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                "ZERODA 폐기물데이터플랫폼",
                font_size="0.85em", font_weight="600", color="#444",
            ),
            rx.text(
                "대표 정석완 · 사업자등록번호 405-11-42991 · 통신판매업신고 미신고",
                font_size="0.75em", color="#666",
            ),
            rx.text(
                "경기도 화성특례시 만세구 남양읍 남양성지로 219, 2층",
                font_size="0.75em", color="#666",
            ),
            rx.text(
                "TEL 031-414-3713 · EMAIL admin@zeroda.co.kr",
                font_size="0.75em", color="#666",
            ),
            rx.hstack(
                rx.link("개인정보처리방침", href="/privacy",
                        font_size="0.75em", color="#0070f3", font_weight="600"),
                rx.text("|", font_size="0.75em", color="#999"),
                rx.link("이용약관", href="/terms",
                        font_size="0.75em", color="#0070f3"),
                rx.text("|", font_size="0.75em", color="#999"),
                rx.link("고객지원", href="mailto:admin@zeroda.co.kr",
                        font_size="0.75em", color="#0070f3"),
                spacing="2",
            ),
            rx.text(
                "© 2026 ZERODA. All rights reserved.",
                font_size="0.7em", color="#999", margin_top="0.3em",
            ),
            spacing="1", align="center",
        ),
        width="100%",
        padding="1.5em 1em",
        margin_top="2em",
        background="#f7f7f8",
        border_top="1px solid #e5e5e5",
    )
