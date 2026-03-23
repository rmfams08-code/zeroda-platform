# modules/driver/collection_input.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.db_manager import db_insert, db_get, get_schools_by_vendor
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_collection_input(user):
    driver_name = user.get('name', '')
    vendor      = user.get('vendor', '')

    st.markdown(f"## 수거 입력")

    schools = get_schools_by_vendor(vendor)
    if not schools:
        st.warning("담당 학교가 없습니다. 관리자에게 문의하세요.")
        return

    # ── 입력 폼 ───────────────────────────
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            school       = st.selectbox("학교 선택 *", schools, key="drv_school")
            collect_date = st.date_input("수거일 *", value=date.today(), key="drv_date")
            item_type    = st.selectbox("품목 *", ["음식물", "재활용", "일반"], key="drv_item")
        with col2:
            weight     = st.number_input("수거량 (kg) *", min_value=0.0, step=0.1, key="drv_weight")
            unit_price = st.number_input("단가 (원)", min_value=0, step=1, key="drv_price")
            collect_time = st.text_input("수거 시간", value=datetime.now().strftime("%H:%M"), key="drv_time")

        memo = st.text_area("메모 (선택)", placeholder="특이사항 입력...", height=80, key="drv_memo")

        # 예상 정산금액 미리보기
        if weight > 0 and unit_price > 0:
            amount = weight * unit_price
            st.info(f"💰 예상 정산금액: {weight:.1f}kg × {unit_price:,}원 = **{amount:,.0f}원**")

    st.divider()

    # ── 버튼 2개: 임시저장 / 수거완료+본사전송 ──
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📋 임시 저장", use_container_width=True):
            if not _validate(school, weight):
                return
            row_id = _save(vendor, school, collect_date, collect_time,
                           item_type, weight, unit_price, driver_name, memo,
                           status='draft')
            if row_id:
                st.success(f"임시 저장 완료 (ID: {row_id})")
            else:
                st.error("저장 실패 - 관리자에게 문의하세요.")

    with col2:
        if st.button("✅ 수거완료 / 본사 전송", type="primary", use_container_width=True):
            if not _validate(school, weight):
                return
            row_id = _save(vendor, school, collect_date, collect_time,
                           item_type, weight, unit_price, driver_name, memo,
                           status='submitted')
            if row_id:
                st.success(f"✅ 본사 전송 완료! (ID: {row_id})")
                st.balloons()
            else:
                st.error("전송 실패 - 관리자에게 문의하세요.")

    st.divider()

    # ── 오늘 입력 현황 ────────────────────
    st.markdown("### 오늘 입력 현황")
    today = str(date.today())
    today_rows = [r for r in db_get('real_collection')
                  if r.get('driver') == driver_name
                  and str(r.get('collect_date', '')) == today]

    if not today_rows:
        st.info("오늘 입력된 수거 실적이 없습니다.")
    else:
        df = pd.DataFrame(today_rows)
        show = [c for c in ['school_name','item_type','weight','status','memo'] if c in df.columns]
        # 상태 한글 표시
        if 'status' in df.columns:
            df['status'] = df['status'].map({'draft': '📋 임시저장', 'submitted': '✅ 전송완료'}).fillna(df['status'])
        st.dataframe(df[show], use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("오늘 수거량", f"{df['weight'].sum() if 'weight' in df.columns else 0:,.1f} kg")
        with c2:
            submitted = len([r for r in today_rows if r.get('status') == 'submitted'])
            st.metric("전송 완료", f"{submitted}건")


def _validate(school, weight):
    if not school or school == '학교 없음':
        st.error("학교를 선택하세요.")
        return False
    if weight <= 0:
        st.error("수거량을 입력하세요.")
        return False
    return True


def _save(vendor, school, collect_date, collect_time,
          item_type, weight, unit_price, driver, memo, status):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data = {
        'vendor':        vendor,
        'school_name':   school,
        'collect_date':  str(collect_date),
        'item_type':     item_type,
        'weight':        weight,
        'unit_price':    unit_price,
        'amount':        weight * unit_price,
        'driver':        driver,
        'memo':          memo,
        'status':        status,
        'submitted_at':  now if status == 'submitted' else '',
        'created_at':    now,
    }
    return db_insert('real_collection', data)
