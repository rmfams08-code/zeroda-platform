# zeroda_platform/auth/account_manager.py
# ==========================================
# 본사 관리자 전용 - 계정 생성/수정/삭제
# ==========================================

import streamlit as st
import hashlib
import sqlite3
from datetime import datetime
from config.settings import DB_PATH, ROLES, ROLE_ICONS
from database.db_manager import db_get, db_upsert, db_delete, get_all_vendors, get_vendor_options, get_vendor_name, get_all_schools


# ──────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_all_accounts(role_filter=None):
    """전체 계정 조회 (역할 필터 옵션)"""
    rows = db_get('users')
    if role_filter and role_filter != '전체':
        rows = [r for r in rows if r.get('role') == role_filter]
    return rows


def create_account(user_id, password, role, name,
                   vendor='', schools='', edu_office=''):
    """계정 생성"""
    # 중복 체크
    existing = db_get('users', {'user_id': user_id})
    if existing:
        return False, "이미 존재하는 아이디입니다."

    ok = db_upsert('users', {
        'user_id':    user_id,
        'pw_hash':    hash_password(password),
        'role':       role,
        'name':       name,
        'vendor':     vendor,
        'schools':    schools,
        'edu_office': edu_office,
        'is_active':  1,
        'created_at': _now(),
        'updated_at': _now(),
    })
    if ok:
        return True, f"계정 '{user_id}' 생성 완료"
    return False, "계정 생성 실패 (DB 오류)"


def update_account(user_id, name=None, password=None,
                   vendor=None, schools=None,
                   edu_office=None, is_active=None):
    """계정 수정 (변경할 항목만 전달)"""
    rows = db_get('users', {'user_id': user_id})
    if not rows:
        return False, "계정을 찾을 수 없습니다."

    user = rows[0]
    updated = dict(user)
    updated['updated_at'] = _now()

    if name       is not None: updated['name']       = name
    if vendor     is not None: updated['vendor']     = vendor
    if schools    is not None: updated['schools']    = schools
    if edu_office is not None: updated['edu_office'] = edu_office
    if is_active  is not None: updated['is_active']  = int(is_active)
    if password:               updated['pw_hash']    = hash_password(password)

    ok = db_upsert('users', updated)
    if ok:
        return True, f"계정 '{user_id}' 수정 완료"
    return False, "계정 수정 실패 (DB 오류)"


def deactivate_account(user_id):
    """계정 비활성화 (삭제 대신 soft delete)"""
    return update_account(user_id, is_active=0)


def delete_account(user_id):
    """계정 완전 삭제 (주의: 복구 불가)"""
    rows = db_get('users', {'user_id': user_id})
    if not rows:
        return False, "계정을 찾을 수 없습니다."
    ok = db_delete('users', {'user_id': user_id})
    if ok:
        return True, f"계정 '{user_id}' 삭제 완료"
    return False, "삭제 실패 (DB 오류)"


def reset_password(user_id, new_password):
    """비밀번호 초기화"""
    return update_account(user_id, password=new_password)


# ──────────────────────────────────────────
# 계정관리 UI (본사 관리자 탭에서 호출)
# ──────────────────────────────────────────

def render_account_management():
    """본사 관리자 - 계정관리 탭 전체 UI"""
    st.markdown("## 👥 계정 관리")

    tab_list, tab_create, tab_edit = st.tabs(["📋 계정 목록", "➕ 계정 생성", "✏️ 계정 수정/삭제"])

    # ── 탭1: 계정 목록 ──────────────────────
    with tab_list:
        role_options = ['전체'] + list(ROLES.keys())
        role_filter = st.selectbox("역할 필터", role_options,
                                   format_func=lambda x: '전체' if x == '전체' else f"{ROLE_ICONS.get(x,'')} {ROLES.get(x, x)}")
        accounts = get_all_accounts(role_filter)

        if not accounts:
            st.info("계정이 없습니다.")
        else:
            import pandas as pd
            df = pd.DataFrame(accounts)
            display_cols = ['user_id', 'name', 'role', 'vendor', 'is_active', 'created_at']
            display_cols = [c for c in display_cols if c in df.columns]
            df_display = df[display_cols].copy()
            df_display['role'] = df_display['role'].map(
                lambda x: f"{ROLE_ICONS.get(x,'')} {ROLES.get(x, x)}")
            df_display['is_active'] = df_display['is_active'].map(
                lambda x: '✅ 활성' if int(x or 1) == 1 else '❌ 비활성')
            df_display.columns = ['아이디', '이름', '역할', '소속업체', '상태', '생성일']
            st.dataframe(df_display, use_container_width=True)
            st.caption(f"총 {len(accounts)}개 계정")

    # ── 탭2: 계정 생성 ──────────────────────
    with tab_create:
        st.markdown("### ➕ 신규 계정 생성")

        col1, col2 = st.columns(2)
        with col1:
            new_id   = st.text_input("아이디 *", key="new_uid", placeholder="영문/숫자 조합")
            new_name = st.text_input("이름 *",   key="new_name")
            new_role = st.selectbox(
                "역할 *", list(ROLES.keys()),
                format_func=lambda x: f"{ROLE_ICONS.get(x,'')} {ROLES.get(x, x)}",
                key="new_role"
            )
        with col2:
            new_pw  = st.text_input("비밀번호 *", key="new_pw",  type="password")
            new_pw2 = st.text_input("비밀번호 확인 *", key="new_pw2", type="password")

        # 역할별 추가 입력
        new_vendor     = ''
        new_schools    = ''
        new_edu_office = ''

        role = st.session_state.get('new_role', 'admin')

        if role in ('vendor_admin', 'driver'):
            vendor_opts = get_vendor_options()  # {표시명: ID}
            if vendor_opts:
                sel_label  = st.selectbox("소속 업체 *", list(vendor_opts.keys()), key="new_vendor_sel")
                new_vendor = vendor_opts[sel_label]  # ID만 저장
                st.caption(f"저장될 업체 ID: `{new_vendor}`")
            else:
                new_vendor = st.text_input("소속 업체 ID *", key="new_vendor_txt",
                                           placeholder="업체를 먼저 등록하세요")

        elif role in ('school_admin', 'school_nutrition'):
            schools = get_all_schools()
            if schools:
                sel = st.multiselect("담당 학교 *", schools, key="new_school_sel")
                new_schools = ','.join(sel)
            else:
                new_schools = st.text_input("담당 학교 (쉼표 구분)", key="new_school_txt")

        elif role == 'edu_office':
            new_edu_office = st.text_input("교육청명 *", key="new_edu")

        if st.button("계정 생성", type="primary", key="btn_create"):
            if not new_id or not new_name or not new_pw:
                st.error("아이디, 이름, 비밀번호는 필수입니다.")
            elif new_pw != new_pw2:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                ok, msg = create_account(
                    new_id, new_pw, role, new_name,
                    vendor=new_vendor,
                    schools=new_schools,
                    edu_office=new_edu_office
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    # ── 탭3: 계정 수정/삭제 ─────────────────
    with tab_edit:
        st.markdown("### ✏️ 계정 수정 / 삭제")

        accounts_all = get_all_accounts()
        if not accounts_all:
            st.info("계정이 없습니다.")
            return

        account_options = {
            f"{ROLE_ICONS.get(a['role'],'')} {a['user_id']} ({a['name']})": a['user_id']
            for a in accounts_all
        }
        selected_label = st.selectbox("수정할 계정 선택", list(account_options.keys()), key="edit_sel")
        selected_id    = account_options[selected_label]

        rows = db_get('users', {'user_id': selected_id})
        if not rows:
            st.warning("계정 정보를 불러올 수 없습니다.")
            return
        user = rows[0]

        col1, col2 = st.columns(2)
        with col1:
            edit_name = st.text_input("이름", value=user.get('name',''), key="edit_name")
            # 업체 선택 - ID 기준
            vendor_opts = get_vendor_options()  # {표시명: ID}
            current_vendor = user.get('vendor', '')
            if vendor_opts:
                # 현재 vendor 값이 ID인지 명인지 모두 대응
                current_ids = list(vendor_opts.values())
                default_idx = current_ids.index(current_vendor) if current_vendor in current_ids else 0
                sel_label   = st.selectbox("소속 업체", list(vendor_opts.keys()),
                                           index=default_idx, key="edit_vendor_sel")
                edit_vendor = vendor_opts[sel_label]
                st.caption(f"저장될 업체 ID: `{edit_vendor}`")
            else:
                edit_vendor = st.text_input("소속 업체 ID", value=current_vendor, key="edit_vendor")
        with col2:
            edit_pw  = st.text_input("새 비밀번호 (변경 시만 입력)", type="password", key="edit_pw")
            edit_active = st.checkbox("활성 계정", value=bool(int(user.get('is_active', 1))), key="edit_active")

        edit_schools = st.text_input("담당 학교 (쉼표 구분)", value=user.get('schools',''), key="edit_schools")
        edit_edu     = st.text_input("교육청명", value=user.get('edu_office',''), key="edit_edu")

        col_save, col_deact, col_del = st.columns(3)

        with col_save:
            if st.button("💾 저장", type="primary", key="btn_save"):
                ok, msg = update_account(
                    selected_id,
                    name=edit_name,
                    password=edit_pw if edit_pw else None,
                    vendor=edit_vendor,
                    schools=edit_schools,
                    edu_office=edit_edu,
                    is_active=edit_active,
                )
                if ok: st.success(msg)
                else:  st.error(msg)

        with col_deact:
            if st.button("⏸️ 비활성화", key="btn_deact"):
                ok, msg = deactivate_account(selected_id)
                if ok: st.success(msg)
                else:  st.error(msg)

        with col_del:
            if st.button("🗑️ 완전 삭제", type="secondary", key="btn_del"):
                st.session_state['confirm_delete'] = selected_id

        # 삭제 확인
        if st.session_state.get('confirm_delete') == selected_id:
            st.warning(f"⚠️ '{selected_id}' 계정을 완전히 삭제합니다. 복구 불가합니다.")
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button("✅ 확인 삭제", key="btn_confirm_del"):
                    ok, msg = delete_account(selected_id)
                    st.session_state.pop('confirm_delete', None)
                    if ok: st.success(msg); st.rerun()
                    else:  st.error(msg)
            with col_no:
                if st.button("❌ 취소", key="btn_cancel_del"):
                    st.session_state.pop('confirm_delete', None)
                    st.rerun()