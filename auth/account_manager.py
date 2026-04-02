# zeroda_platform/auth/account_manager.py
# ==========================================
# 본사 관리자 전용 - 계정 생성/수정/삭제
# 수정4: 계정관리 전면 개편 (역할별 소속 동적 UI + 수정 시 기존정보 로드 수정)
# ==========================================

import streamlit as st
import hashlib
import sqlite3
from datetime import datetime
from config.settings import DB_PATH, ROLES, ROLE_ICONS
from database.db_manager import (
    db_get, db_upsert, db_delete,
    get_all_vendors, get_vendor_options, get_vendor_name, get_all_schools,
)


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
# 역할별 소속정보 표시 헬퍼
# ──────────────────────────────────────────

def _get_affiliation_display(account: dict) -> str:
    """역할에 따라 소속/담당 정보를 문자열로 반환"""
    role = account.get('role', '')
    if role in ('vendor_admin', 'driver'):
        vid = account.get('vendor', '')
        if vid:
            vname = get_vendor_name(vid)
            return f"{vname} ({vid})" if vname and vname != vid else vid
        return '-'
    elif role in ('school_admin', 'school_nutrition', 'meal_manager'):
        schools = account.get('schools', '')
        return schools if schools else '-'
    elif role == 'edu_office':
        return account.get('edu_office', '') or '-'
    else:
        return '-'


def _render_role_fields(role: str, prefix: str,
                        current_vendor='', current_schools='', current_edu=''):
    """
    역할에 따라 소속 입력 필드를 동적으로 렌더링.
    prefix: 'new' 또는 'edit' (key 충돌 방지용)
    current_*: 수정 모드에서 기존값 (생성 모드에서는 빈값)

    Returns: (vendor, schools, edu_office)
    """
    vendor = ''
    schools = ''
    edu_office = ''

    # ── 업체 소속 (vendor_admin, driver) ──
    if role in ('vendor_admin', 'driver'):
        st.markdown("**📦 소속 업체**")
        vendor_opts = get_vendor_options()   # {표시명: ID}
        if vendor_opts:
            opt_keys  = list(vendor_opts.keys())
            opt_vals  = list(vendor_opts.values())
            default_idx = 0
            if current_vendor and current_vendor in opt_vals:
                default_idx = opt_vals.index(current_vendor)
            sel_label = st.selectbox(
                "소속 업체 *", opt_keys,
                index=default_idx, key=f"{prefix}_vendor_sel"
            )
            vendor = vendor_opts[sel_label]
            st.caption(f"저장될 업체 ID: `{vendor}`")
        else:
            vendor = st.text_input(
                "소속 업체 ID *", value=current_vendor,
                key=f"{prefix}_vendor_txt",
                placeholder="업체를 먼저 등록하세요"
            )

    # ── 담당 학교/급식소 (school_admin, school_nutrition, meal_manager) ──
    elif role in ('school_admin', 'school_nutrition', 'meal_manager'):
        label = "담당 급식소(학교)" if role == 'meal_manager' else "담당 학교"
        st.markdown(f"**🏫 {label}**")
        all_schools = get_all_schools()
        # 기존값 파싱
        current_list = [s.strip() for s in current_schools.split(',') if s.strip()] \
            if current_schools else []
        if all_schools:
            # 기존값 중 목록에 없는 것도 선택지에 포함
            combined = list(dict.fromkeys(all_schools + current_list))
            sel = st.multiselect(
                f"{label} *", combined,
                default=current_list, key=f"{prefix}_school_sel"
            )
            schools = ','.join(sel)
        else:
            schools = st.text_input(
                f"{label} (쉼표 구분)", value=current_schools,
                key=f"{prefix}_school_txt"
            )

    # ── 교육청 (edu_office) ──
    elif role == 'edu_office':
        st.markdown("**🏛️ 교육청명**")
        edu_office = st.text_input(
            "교육청명 *", value=current_edu,
            key=f"{prefix}_edu"
        )

    # admin은 소속 필드 없음
    return vendor, schools, edu_office


# ──────────────────────────────────────────
# 계정관리 메인 UI (4탭 구조)
# ──────────────────────────────────────────

def render_account_management():
    """본사 관리자 - 계정관리 탭 전체 UI"""
    st.markdown("## 👥 계정 관리")

    tab_list, tab_create, tab_edit, tab_delete = st.tabs([
        "📋 계정 목록", "➕ 계정 생성", "✏️ 계정 수정", "🗑️ 비활성화/삭제"
    ])

    # ══════════════════════════════════════
    # 탭1: 계정 목록
    # ══════════════════════════════════════
    with tab_list:
        role_options = ['전체'] + list(ROLES.keys())
        role_filter = st.selectbox(
            "역할 필터", role_options,
            format_func=lambda x: '전체' if x == '전체'
                else f"{ROLE_ICONS.get(x,'')} {ROLES.get(x, x)}",
            key="acct_list_filter"
        )
        accounts = get_all_accounts(role_filter)

        if not accounts:
            st.info("계정이 없습니다.")
        else:
            import pandas as pd
            rows_display = []
            for a in accounts:
                rows_display.append({
                    '아이디':    a.get('user_id', ''),
                    '이름':      a.get('name', ''),
                    '역할':      f"{ROLE_ICONS.get(a.get('role',''),'')} "
                                 f"{ROLES.get(a.get('role',''), a.get('role',''))}",
                    '소속/담당':  _get_affiliation_display(a),
                    '상태':      '✅ 활성' if int(a.get('is_active', 1)) == 1
                                 else '❌ 비활성',
                    '생성일':    a.get('created_at', '')[:10],
                })
            df = pd.DataFrame(rows_display)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"총 {len(accounts)}개 계정")

    # ══════════════════════════════════════
    # 탭2: 계정 생성
    # ══════════════════════════════════════
    with tab_create:
        st.markdown("### ➕ 신규 계정 생성")

        col1, col2 = st.columns(2)
        with col1:
            new_id   = st.text_input("아이디 *", key="new_uid",
                                     placeholder="영문/숫자 조합")
            new_name = st.text_input("이름 *", key="new_name")
            new_role = st.selectbox(
                "역할 *", list(ROLES.keys()),
                format_func=lambda x: f"{ROLE_ICONS.get(x,'')} {ROLES.get(x, x)}",
                key="new_role"
            )
        with col2:
            new_pw  = st.text_input("비밀번호 *", key="new_pw", type="password")
            new_pw2 = st.text_input("비밀번호 확인 *", key="new_pw2", type="password")

        # 역할별 소속 필드 (동적)
        role = st.session_state.get('new_role', 'admin')
        new_vendor, new_schools, new_edu = _render_role_fields(role, 'new')

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
                    edu_office=new_edu,
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    # ══════════════════════════════════════
    # 탭3: 계정 수정
    # ══════════════════════════════════════
    with tab_edit:
        st.markdown("### ✏️ 계정 수정")

        accounts_all = get_all_accounts()
        if not accounts_all:
            st.info("계정이 없습니다.")
        else:
            account_options = {
                f"{ROLE_ICONS.get(a['role'],'')} {a['user_id']} ({a['name']})": a['user_id']
                for a in accounts_all
            }
            selected_label = st.selectbox(
                "수정할 계정 선택", list(account_options.keys()),
                key="edit_sel"
            )
            selected_id = account_options[selected_label]

            rows = db_get('users', {'user_id': selected_id})
            if not rows:
                st.warning("계정 정보를 불러올 수 없습니다.")
            else:
                user = rows[0]
                user_role = user.get('role', 'admin')

                # ── 현재 정보 표시 ──
                st.info(
                    f"**현재 정보** — "
                    f"역할: {ROLE_ICONS.get(user_role,'')} {ROLES.get(user_role, user_role)} | "
                    f"소속: {_get_affiliation_display(user)} | "
                    f"상태: {'✅ 활성' if int(user.get('is_active',1)) else '❌ 비활성'}"
                )

                st.divider()

                # ── 수정 폼 ──
                col1, col2 = st.columns(2)
                with col1:
                    edit_name = st.text_input(
                        "이름", value=user.get('name', ''),
                        key="edit_name"
                    )
                with col2:
                    edit_pw = st.text_input(
                        "새 비밀번호 (변경 시만 입력)", type="password",
                        key="edit_pw"
                    )

                # ── 역할별 소속 필드 (기존값 로드) ──
                edit_vendor, edit_schools, edit_edu = _render_role_fields(
                    user_role, 'edit',
                    current_vendor=user.get('vendor', ''),
                    current_schools=user.get('schools', ''),
                    current_edu=user.get('edu_office', ''),
                )

                # ── 활성/비활성 ──
                edit_active = st.checkbox(
                    "활성 계정",
                    value=bool(int(user.get('is_active', 1))),
                    key="edit_active"
                )

                if st.button("💾 저장", type="primary", key="btn_save",
                             use_container_width=True):
                    ok, msg = update_account(
                        selected_id,
                        name=edit_name,
                        password=edit_pw if edit_pw else None,
                        vendor=edit_vendor,
                        schools=edit_schools,
                        edu_office=edit_edu,
                        is_active=edit_active,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

    # ══════════════════════════════════════
    # 탭4: 비활성화/삭제
    # ══════════════════════════════════════
    with tab_delete:
        st.markdown("### 🗑️ 계정 비활성화 / 삭제")
        st.caption("비활성화는 로그인 차단(복구 가능), 완전 삭제는 복구 불가입니다.")

        accounts_all2 = get_all_accounts()
        if not accounts_all2:
            st.info("계정이 없습니다.")
        else:
            del_options = {
                f"{ROLE_ICONS.get(a['role'],'')} {a['user_id']} ({a['name']}) "
                f"{'✅' if int(a.get('is_active',1)) else '❌'}": a['user_id']
                for a in accounts_all2
            }
            del_label = st.selectbox(
                "대상 계정 선택", list(del_options.keys()),
                key="del_sel"
            )
            del_id = del_options[del_label]

            del_rows = db_get('users', {'user_id': del_id})
            if del_rows:
                du = del_rows[0]
                st.info(
                    f"**{du.get('name','')}** ({du.get('user_id','')}) — "
                    f"{ROLES.get(du.get('role',''), du.get('role',''))} | "
                    f"소속: {_get_affiliation_display(du)}"
                )

            col_deact, col_del = st.columns(2)

            with col_deact:
                if st.button("⏸️ 비활성화", key="btn_deact",
                             use_container_width=True):
                    ok, msg = deactivate_account(del_id)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            with col_del:
                if st.button("🗑️ 완전 삭제", type="secondary", key="btn_del",
                             use_container_width=True):
                    st.session_state['confirm_delete'] = del_id

            # 삭제 확인
            if st.session_state.get('confirm_delete') == del_id:
                st.warning(
                    f"⚠️ '{del_id}' 계정을 완전히 삭제합니다. **복구 불가**합니다."
                )
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ 확인 삭제", key="btn_confirm_del"):
                        ok, msg = delete_account(del_id)
                        st.session_state.pop('confirm_delete', None)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with col_no:
                    if st.button("❌ 취소", key="btn_cancel_del"):
                        st.session_state.pop('confirm_delete', None)
                        st.rerun()
