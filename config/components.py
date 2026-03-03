# config/components.py
# 재사용 가능한 UI 컴포넌트
import streamlit as st


def apply_css():
    """공통 CSS 적용 - 모든 페이지 상단에서 호출"""
    from config.styles import COMMON_CSS
    st.markdown(COMMON_CSS, unsafe_allow_html=True)


def metric_card(title: str, value: str, subtitle: str = None, color: str = '#1a73e8'):
    """
    통일된 메트릭 카드
    사용: metric_card("총 수거량", "1,234 kg", subtitle="전월比 +12%")
    """
    sub_html = f'<div style="font-size:12px;color:#5f6368;margin-top:4px;">{subtitle}</div>' if subtitle else ''
    st.markdown(f"""
    <div style="background:#fff;border-radius:12px;padding:16px 20px;
                box-shadow:0 2px 8px rgba(0,0,0,0.06);
                border-left:5px solid {color};margin-bottom:12px;">
        <div style="font-size:13px;color:#5f6368;font-weight:600;">{title}</div>
        <div style="font-size:24px;font-weight:900;color:{color};margin-top:4px;">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def status_badge(status: str) -> str:
    """
    수거 상태 배지 HTML 반환
    사용: st.markdown(status_badge('confirmed'), unsafe_allow_html=True)
    """
    STATUS_MAP = {
        'draft':     ('📋 임시저장', 'badge-draft'),
        'submitted': ('📤 전송완료', 'badge-submitted'),
        'confirmed': ('✅ 확인완료', 'badge-confirmed'),
        'rejected':  ('❌ 반려',     'badge-rejected'),
    }
    label, css_class = STATUS_MAP.get(status, (status, 'badge-draft'))
    return f'<span class="{css_class}">{label}</span>'


def section_header(title: str, icon: str = ''):
    """섹션 헤더"""
    st.markdown(f"""
    <div class="section-header">{icon} {title}</div>
    """, unsafe_allow_html=True)


def empty_state(message: str = '데이터가 없습니다.', icon: str = '📭'):
    """데이터 없음 상태"""
    st.markdown(f"""
    <div style="text-align:center;padding:40px 20px;color:#9aa0a6;">
        <div style="font-size:48px;margin-bottom:12px;">{icon}</div>
        <div style="font-size:16px;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


def alert_box(message: str, type: str = 'info'):
    """
    알림 박스
    type: 'info' | 'success' | 'warning' | 'error'
    """
    configs = {
        'info':    ('#e8f0fe', '#1a73e8', 'ℹ️'),
        'success': ('#e6f4ea', '#34a853', '✅'),
        'warning': ('#fef7e0', '#f9ab00', '⚠️'),
        'error':   ('#fce8e6', '#ea4335', '❌'),
    }
    bg, color, icon = configs.get(type, configs['info'])
    st.markdown(f"""
    <div style="background:{bg};border-left:4px solid {color};
                padding:12px 16px;border-radius:8px;margin-bottom:12px;">
        {icon} <span style="color:{color};font-weight:600;">{message}</span>
    </div>
    """, unsafe_allow_html=True)


def data_table(df, key: str = None, height: int = None):
    """스타일 적용된 데이터프레임"""
    kwargs = {'use_container_width': True, 'hide_index': True}
    if height:
        kwargs['height'] = height
    st.dataframe(df, **kwargs)


def progress_bar(label: str, value: float, max_value: float, color: str = '#1a73e8'):
    """진행 바"""
    pct = min(int((value / max_value * 100) if max_value > 0 else 0), 100)
    st.markdown(f"""
    <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
            <span>{label}</span><span style="color:{color};font-weight:700;">{pct}%</span>
        </div>
        <div style="background:#e8eaed;border-radius:4px;height:8px;">
            <div style="background:{color};width:{pct}%;height:8px;border-radius:4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
