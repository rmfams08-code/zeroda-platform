# zeroda_platform/modules/driver/collection_input.py
# ==========================================
# 수거기사 - 수거 실적 입력 (모바일 최적화)
# ==========================================

import streamlit as st
from datetime import date, datetime
from database.db_manager import (
    db_get, db_upsert, load_schedule,
    get_schools_by_vendor, get_vendor_display_name
)


def render_collection_input(user: dict):
    st.markdown("## 📝 수거 실적 입력")

    vendor = user.get('vendor', '')
    name   = user.get('name', '')

    today    = date.today()
    today_wd = {0:'월',1:'화',2:'수',3:'목',4:'금',5:'토',6:'일'}[today.weekday()]

    # 오늘 일정 기반 학교 목록 우선
    sched          = load_schedule(vendor, today.month)
    sched_schools  = []
    if sched and today_wd in sched.get('요일', []):
        sched_schools = sched.get('학교', [])

    all_schools = get_schools_by_vendor(vendor)
    school_options = sched_schools if sched_schools else all_schools

    if not school_options:
        st.warning("배정된 학교가 없습니다.")
        return

    # ── 입력 폼 ──
    st.markdown(f"**{today.strftime('%Y년 %m월 %d일')} ({today_wd}요일)**")

    school   = st.selectbox("학교 선택 *", school_options, key="drv_school")
    date_sel = st.date_input("수거 날짜", value=today, key="drv_date")

    col1, col2 = st.columns(2)
    with col1:
        food_kg = st.number_input("음식물 (kg)", min_value=0.0,
                                   step=0.1, key="drv_food")
        biz_kg  = st.number_input("사업장 (kg)", min_value=0.0,
                                   step=0.1, key="drv_biz")
    with col2:
        recycle_kg = st.number_input("재활용 (kg)", min_value=0.0,
                                      step=0.1, key="drv_recycle")
        time_v     = st.text_input("수거 시간",
                                    value=datetime.now().strftime('%H:%M'),
                                    key="drv_time")

    # 계약 단가 조회
    price_rows  = db_get('contract_data', {'vendor': vendor})
    price_dict  = {r['item']: int(r['price']) for r in price_rows}
    food_price  = price_dict.get('음식물',   162)
    biz_price   = price_dict.get('사업장',   200)

    food_amt = int(food_kg * food_price)
    biz_amt  = int(biz_kg  * biz_price)
    total    = food_amt + biz_amt

    if food_kg > 0 or biz_kg > 0:
        st.markdown(f"""
        <div style="background:#e8f4fd;border-radius:8px;padding:12px;margin:8px 0;">
            <div style="font-weight:700;color:#1a73e8;">예상 정산금액</div>
            <div>음식물: {food_kg:.1f}kg × {food_price:,}원 = {food_amt:,}원</div>
            <div>사업장: {biz_kg:.1f}kg × {biz_price:,}원 = {biz_amt:,}원</div>
            <div style="font-weight:900;font-size:18px;color:#1a73e8;">합계: {total:,}원</div>
        </div>""", unsafe_allow_html=True)

    memo = st.text_area("메모 (선택)", key="drv_memo", placeholder="특이사항 입력...")

    if st.button("✅ 수거 완료 등록", type="primary",
                 use_container_width=True, key="btn_drv_save"):
        if food_kg <= 0 and recycle_kg <= 0 and biz_kg <= 0:
            st.error("수거량을 1개 이상 입력하세요.")
            return

        date_str = str(date_sel)
        supply   = int(food_amt / 1.1)
        vat      = food_amt - supply

        ok = db_upsert('real_collection', {
            '날짜':        date_str,
            '학교명':      school,
            '음식물(kg)':  food_kg,
            '단가(원)':    food_price,
            '공급가':      supply,
            '재활용(kg)':  recycle_kg,
            '사업장(kg)':  biz_kg,
            '월':          date_sel.month,
            '년도':        str(date_sel.year),
            '수거업체':    vendor,
            '수거기사':    name,
            '수거시간':    time_v,
            '재활용방법':  memo,
        })
        if ok:
            st.success(f"✅ {school} 수거 완료 등록!")
            st.balloons()
        else:
            st.error("저장 실패. 다시 시도하세요.")

    # ── 오늘 입력 현황 ──
    st.divider()
    st.markdown("### 오늘 입력 현황")
    today_str  = str(today)
    today_rows = db_get('real_collection')
    today_rows = [r for r in today_rows
                  if r.get('날짜') == today_str
                  and r.get('수거기사') == name]

    if not today_rows:
        st.info("오늘 입력된 수거 실적이 없습니다.")
        return

    for r in today_rows:
        kg = float(r.get('음식물(kg)', 0) or 0)
        st.markdown(
            f"✅ **{r.get('학교명','')}** — {kg:.1f}kg "
            f"({r.get('수거시간','')})")