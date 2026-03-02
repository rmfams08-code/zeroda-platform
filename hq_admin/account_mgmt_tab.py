# zeroda_platform/modules/hq_admin/account_mgmt_tab.py
# ==========================================
# 본사 관리자 - 계정관리 탭 (auth 연결)
# ==========================================

from auth.account_manager import render_account_management


def render_account_mgmt_tab():
    """auth/account_manager.py UI를 그대로 호출"""
    render_account_management()