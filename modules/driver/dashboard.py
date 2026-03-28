# modules/driver/dashboard.py
# 기사 전용 앱 - 단일 화면 (안전점검 → 수거일정 → 퇴근)
import streamlit as st
import pandas as pd
import urllib.parse
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from database.db_manager import db_insert, db_get, get_schools_by_vendor
from config.settings import COMMON_CSS

WEEKDAY_MAP = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}


# ── 숫자 키패드 (모바일 터치 최적화) ──────────────────────────────
_NUMPAD_CSS = """
<style>
/* ── 모바일 키패드 최적화 ── */
/* 모바일에서 st.columns 가로 정렬 유지 (세로 쌓임 방지) */
@media (max-width: 768px) {
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
    }
    [data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        min-width: 0 !important;
        flex: 1 1 0 !important;
    }
}
/* 키패드 버튼 터치 영역 확대 */
[data-testid="stButton"] button {
    min-height: 52px !important;
    font-size: 18px !important;
    touch-action: manipulation !important;
}
</style>
"""

def _render_numpad(dr_key: str, school: str):
    """
    전체 너비 4×4 숫자 키패드.
    _np_target_{school} : 편집 중인 행 인덱스 (-1이면 닫힘)
    _np_buf_{school}    : 입력 버퍼 문자열
    """
    _tgt_key = f"_np_target_{school}"
    _buf_key = f"_np_buf_{school}"
    tgt = st.session_state.get(_tgt_key, -1)
    if tgt < 0:
        return  # 키패드 닫힘

    # 모바일 CSS 주입 (키패드 열릴 때만)
    st.markdown(_NUMPAD_CSS, unsafe_allow_html=True)

    buf = st.session_state.get(_buf_key, "")
    display = buf if buf else "0"

    st.markdown(f"**수거량 입력** &nbsp; 👉 &nbsp; "
                f"<span style='font-size:28px;font-weight:bold;color:#1a73e8'>"
                f"{display} kg</span>",
                unsafe_allow_html=True)

    # 4×4 키패드 레이아웃
    _rows = [
        ['7', '8', '9', '⌫'],
        ['4', '5', '6', 'C'],
        ['1', '2', '3', '.'],
        ['0', '00', '✅', '🗑️'],
    ]
    _pressed = None
    for _r in _rows:
        _c = st.columns(4)
        for _col, _k in zip(_c, _r):
            with _col:
                _btn_type = "primary" if _k == '✅' else "secondary"
                if st.button(_k, key=f"_np_{school}_{_k}",
                             use_container_width=True, type=_btn_type):
                    _pressed = _k

    # 버튼 입력 처리
    if _pressed:
        v = st.session_state.get(_buf_key, "")
        if _pressed == '⌫':
            st.session_state[_buf_key] = v[:-1]
        elif _pressed == 'C':
            st.session_state[_buf_key] = ""
        elif _pressed == '.':
            if '.' not in v:
                st.session_state[_buf_key] = v + '.'
        elif _pressed == '00':
            st.session_state[_buf_key] = v + '00'
        elif _pressed == '✅':
            # 확인 — 값 저장 후 키패드 닫기
            try:
                _val = float(v) if v.strip() else 0.0
            except ValueError:
                _val = 0.0
            if 0 <= tgt < len(st.session_state.get(dr_key, [])):
                st.session_state[dr_key][tgt]["weight"] = _val
            st.session_state[_tgt_key] = -1
            st.session_state[_buf_key] = ""
        elif _pressed == '🗑️':
            st.session_state[_buf_key] = ""
        else:
            st.session_state[_buf_key] = v + _pressed
        st.rerun()

# ── 음성 입력 헬퍼 (Web Speech API) ───────────────────────────────
import streamlit.components.v1 as components
import re

def _render_voice_input(schools: list, school_key_prefix: str):
    """
    마이크 버튼 → 음성 인식 → '거래처명 품목 수거량' 파싱
    → confirm 팝업 → 확인 시 postMessage 로 부모에 전달
    → 숨겨진 리스너 컴포넌트가 session_state 에 저장 → 자동 입력
    (하드 리로드 없음 — 튕김 현상 해결)
    """
    _schools_js = json.dumps(schools, ensure_ascii=False)

    # ── (A) 메시지 수신 리스너 (부모 페이지에 삽입, 높이 0) ──
    _listener_html = """
    <script>
    window.addEventListener('message', function(e) {
      if (e.data && e.data.type === 'VOICE_CONFIRMED') {
        // Streamlit 의 setComponentValue 가 없으므로
        // hidden input → form submit 패턴으로 session_state 전달
        const d = e.data;
        const frame = window.parent;
        try {
          // Streamlit 내부 API: query_params 를 soft 하게 설정
          const url = new URL(frame.location.href);
          url.searchParams.set('_vc', '1');
          url.searchParams.set('_vc_school', d.school);
          url.searchParams.set('_vc_weight', d.weight.toString());
          url.searchParams.set('_vc_item', d.item);
          // history.replaceState 는 페이지 리로드 없이 URL 만 변경
          frame.history.replaceState(null, '', url.toString());
          // Streamlit 의 soft rerun 트리거
          // StreamlitのWidgetManager 에 rerun 시그널
          const rerunBtn = frame.document.querySelector(
            '[data-testid="stRerunButton"], [data-testid="stStatusWidget"] button'
          );
          if (rerunBtn) { rerunBtn.click(); }
          else {
            // fallback: 키보드 이벤트로 rerun
            frame.document.dispatchEvent(
              new KeyboardEvent('keydown', {key: 'r', ctrlKey: false})
            );
            // 최종 fallback: soft reload
            setTimeout(function() { frame.location.reload(); }, 300);
          }
        } catch(ex) {
          // sandbox 제한 시 fallback
          frame.location.reload();
        }
      }
    });
    </script>
    """
    components.html(_listener_html, height=0)

    # ── (B) 음성인식 + confirm 팝업 컴포넌트 ──
    _html = f"""
    <div id="voice-box" style="text-align:center;padding:8px 0">
      <button id="mic-btn" onclick="startVoice()" style="
        width:100%;max-width:400px;padding:14px 20px;font-size:18px;font-weight:700;
        border:2px solid #1a73e8;border-radius:12px;background:#fff;color:#1a73e8;
        cursor:pointer;touch-action:manipulation">
        🎤 음성으로 입력하기
      </button>
      <div id="mic-status" style="margin-top:8px;font-size:14px;color:#666"></div>
      <div id="mic-result" style="margin-top:6px;font-size:16px;font-weight:700;color:#333;
        min-height:24px"></div>
    </div>
    <script>
    const schools = {_schools_js};
    const itemKeywords = {{
      '음식물': ['음식물', '음식', '잔반', '급식'],
      '재활용': ['재활용', '분리수거', '페트', '캔'],
      '일반':   ['일반', '종량제', '생활']
    }};
    let recognition = null;

    function findSchool(text) {{
      let best = null, bestLen = 0;
      for (const s of schools) {{
        if (text.includes(s) && s.length > bestLen) {{
          best = s;
          bestLen = s.length;
        }}
      }}
      if (!best) {{
        for (const s of schools) {{
          const short = s.replace(/등학교|학교|중$|고$/, '');
          if (short.length >= 2 && text.includes(short) && short.length > bestLen) {{
            best = s;
            bestLen = short.length;
          }}
        }}
      }}
      return best;
    }}

    function findItem(text) {{
      for (const [item, keywords] of Object.entries(itemKeywords)) {{
        for (const kw of keywords) {{
          if (text.includes(kw)) return item;
        }}
      }}
      return '음식물';
    }}

    function findWeight(text) {{
      const nums = text.match(/\\d+\\.?\\d*/g);
      if (nums && nums.length > 0) {{
        return parseFloat(nums[nums.length - 1]);
      }}
      return null;
    }}

    function applyVoiceResult(school, item, weight) {{
      // postMessage 로 부모 프레임의 리스너에 전달 (하드 리로드 없음)
      window.parent.postMessage({{
        type: 'VOICE_CONFIRMED',
        school: school,
        item: item,
        weight: weight
      }}, '*');
      document.getElementById('mic-result').innerHTML =
        '<span style="color:#34a853;font-size:18px;">✅ ' + school
        + ' / ' + item + ' / ' + weight + 'kg 등록 중...</span>';
    }}

    function startVoice() {{
      if (recognition) {{
        try {{ recognition.abort(); }} catch(ex) {{}}
        recognition = null;
      }}
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SR) {{
        document.getElementById('mic-status').textContent =
          '⚠️ 이 브라우저는 음성 인식을 지원하지 않습니다 (Chrome 사용 권장)';
        return;
      }}
      recognition = new SR();
      recognition.lang = 'ko-KR';
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 3;

      const btn = document.getElementById('mic-btn');
      const status = document.getElementById('mic-status');
      const result = document.getElementById('mic-result');

      btn.style.background = '#ea4335';
      btn.style.color = '#fff';
      btn.style.border = '2px solid #ea4335';
      btn.textContent = '🔴 듣고 있습니다...';
      btn.disabled = true;
      status.textContent = '말씀해 주세요 (예: "안산고등학교 음식물 200")';
      result.textContent = '';

      function resetBtn() {{
        btn.style.background = '#fff';
        btn.style.color = '#1a73e8';
        btn.style.border = '2px solid #1a73e8';
        btn.textContent = '🎤 다시 입력하기';
        btn.disabled = false;
      }}

      recognition.onresult = function(e) {{
        let final_text = '';
        let interim_text = '';
        for (let i = 0; i < e.results.length; i++) {{
          if (e.results[i].isFinal) {{
            final_text += e.results[i][0].transcript;
          }} else {{
            interim_text += e.results[i][0].transcript;
          }}
        }}
        if (interim_text) {{
          status.textContent = '🔊 ' + interim_text;
        }}
        if (final_text) {{
          const school = findSchool(final_text);
          const weight = findWeight(final_text);
          const item   = findItem(final_text);

          if (school && weight !== null && weight > 0) {{
            result.innerHTML = '🗣️ "' + final_text + '"<br>'
              + '📍 <b>' + school + '</b> / '
              + '📦 <b>' + item + '</b> / '
              + '⚖️ <b>' + weight + 'kg</b>';

            setTimeout(function() {{
              const ok = confirm(
                school + ' / ' + item + ' / ' + weight + 'kg\\n\\n'
                + '수거 등록하시겠습니까?'
              );
              if (ok) {{
                applyVoiceResult(school, item, weight);
              }} else {{
                status.textContent = '❌ 취소됨 — 다시 말씀해 주세요';
              }}
            }}, 200);
          }} else {{
            let msg = '🗣️ "' + final_text + '"<br>';
            if (!school) msg += '⚠️ 거래처 인식 실패&nbsp;&nbsp;';
            else msg += '📍 거래처: <b>' + school + '</b>&nbsp;&nbsp;';
            if (weight === null || weight <= 0) msg += '⚠️ 수거량 인식 실패';
            else msg += '⚖️ 수거량: <b>' + weight + 'kg</b>';
            msg += '<br><span style="font-size:13px;color:#888;">다시 말씀해 주세요 (예: "강남중학교 음식물 200")</span>';
            result.innerHTML = msg;
          }}
        }}
      }};

      recognition.onerror = function(e) {{
        resetBtn();
        if (e.error === 'no-speech') {{
          status.textContent = '⚠️ 음성이 감지되지 않았습니다. 다시 시도하세요.';
        }} else if (e.error === 'not-allowed') {{
          status.textContent = '⚠️ 마이크 권한을 허용해 주세요.';
        }} else if (e.error === 'aborted') {{
          status.textContent = '';
        }} else {{
          status.textContent = '⚠️ 오류: ' + e.error;
        }}
      }};

      recognition.onend = function() {{
        resetBtn();
        if (!result.innerHTML) {{
          status.textContent = '음성 인식 종료';
        }}
      }};

      recognition.start();
    }}
    </script>
    """
    components.html(_html, height=160)


# 안전점검 항목 (확장 가능)
SAFETY_CHECKS = [
    ("chk_camera",    "차량 후방 카메라 정상 작동"),
    ("chk_assistant", "조수석 안전 요원 탑승 확인"),
    ("chk_schoolzone","스쿨존 서행 운행 숙지"),
    ("chk_brake",     "브레이크 작동 정상 확인"),
    ("chk_tire",      "타이어 공기압 이상 없음"),
]


def render_dashboard(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    driver_name = user.get('name', '')
    vendor      = user.get('vendor', '')
    today       = datetime.now(ZoneInfo('Asia/Seoul')).date()
    today_str   = str(today)
    today_wd    = WEEKDAY_MAP[today.weekday()]

    # ── 음성인식 자동입력 수신 처리 ──────────────────
    _vc_params = st.query_params
    if _vc_params.get('_vc') == '1':
        _vc_school = _vc_params.get('_vc_school', '')
        _vc_weight_str = _vc_params.get('_vc_weight', '0')
        _vc_item = _vc_params.get('_vc_item', '음식물')
        # 쿼리 파라미터 즉시 제거 (재진입 방지)
        st.query_params.clear()
        try:
            _vc_weight = float(_vc_weight_str)
        except (ValueError, TypeError):
            _vc_weight = 0.0
        if _vc_school and _vc_weight > 0:
            _dr_key = f"drv_date_rows_{_vc_school}"
            if _dr_key not in st.session_state:
                st.session_state[_dr_key] = [
                    {"date": today, "weight": 0.0, "item": _vc_item}
                ]
            _rows = st.session_state[_dr_key]
            _applied = False
            for _r in _rows:
                if _r["weight"] == 0.0:
                    _r["weight"] = _vc_weight
                    _r["item"] = _vc_item
                    _applied = True
                    break
            if not _applied:
                # 빈 행이 없으면 새 행 추가
                st.session_state[_dr_key].append(
                    {"date": today, "weight": _vc_weight, "item": _vc_item}
                )
                _applied = True
            if _applied:
                st.session_state["_voice_success"] = (
                    f"✅ 음성입력 완료: {_vc_school} / {_vc_item} / {_vc_weight}kg"
                )

    # 음성입력 성공 알림 (rerun 후 1회 표시)
    _voice_msg = st.session_state.pop("_voice_success", None)
    if _voice_msg:
        st.toast(_voice_msg, icon="🎤")

    # ── 헤더 ──────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a73e8,#34a853);
                padding:20px;border-radius:12px;text-align:center;margin-bottom:16px;">
        <div style="color:white;font-size:22px;font-weight:900;">🚚 수거기사 전용 앱</div>
        <div style="color:rgba(255,255,255,0.85);font-size:14px;margin-top:6px;">
            {driver_name} 기사님 &nbsp;|&nbsp; 📅 {today.strftime('%Y.%m.%d')} ({today_wd}요일)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # 섹션1: 안전점검
    # ══════════════════════════════════════════════
    with st.expander("🚨 운행 전 안전점검", expanded=True):
        st.caption("출발 전 반드시 확인하세요.")

        results = {}
        for key, label in SAFETY_CHECKS:
            results[key] = st.checkbox(label, key=key)

        checked_count = sum(results.values())
        total_count   = len(SAFETY_CHECKS)
        _safe_ratio = (checked_count / total_count) if total_count > 0 else 0.0
        _safe_ratio = max(0.0, min(1.0, _safe_ratio))
        st.progress(_safe_ratio)
        st.caption(f"{checked_count} / {total_count} 항목 완료")

        if checked_count == total_count:
            st.success("✅ 모든 안전점검 완료! 안전 운행하세요. 🚦")
        else:
            st.warning(f"⚠️ {total_count - checked_count}개 항목을 확인해 주세요.")

        st.divider()

        # 스쿨존 GPS 알림 토글
        st.markdown("### 🚸 스쿨존 알림")
        schoolzone = st.toggle("스쿨존 진입 알림 활성화", key="schoolzone_toggle")
        if schoolzone:
            st.error("🚨 스쿨존 진입! 속도를 30km 이하로 줄이세요.")
            st.markdown("""
            <div style="text-align:center;background:#d93025;border-radius:50%;
                        width:120px;height:120px;margin:0 auto;
                        display:flex;align-items:center;justify-content:center;">
                <span style="color:white;font-size:56px;font-weight:900;">30</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;color:#d93025;font-weight:700;margin-top:8px;'>제한속도 30km/h</div>",
                        unsafe_allow_html=True)
        else:
            st.info("스쿨존 구역 진입 시 토글을 켜세요.")

    st.divider()

    # ══════════════════════════════════════════════
    # 섹션2: 오늘 수거일정
    # ══════════════════════════════════════════════
    st.markdown("### 📅 수거일정")

    # ── 날짜 필터 ──────────────────────────────
    _col_date, _col_today = st.columns([3, 1])
    with _col_date:
        _sel_date = st.date_input(
            "날짜 선택",
            value=st.session_state.get(
                "drv_schedule_date",
                datetime.now(ZoneInfo('Asia/Seoul')).date()
            ),
            key="drv_schedule_date"
        )
    with _col_today:
        st.write("")  # 간격 맞춤
        if st.button("오늘", key="drv_today_btn",
                     use_container_width=True):
            st.session_state["drv_schedule_date"] = \
                datetime.now(ZoneInfo('Asia/Seoul')).date()
            st.rerun()

    # ── 선택일 요일 계산 ───────────────────────
    _weekday_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
    _sel_weekday = _weekday_map[_sel_date.weekday()]
    _sel_month   = _sel_date.strftime('%Y-%m')
    st.caption(f"📅 {_sel_date} ({_sel_weekday}요일) 수거 일정")

    # ── schedules에서 해당 날짜 일정 필터 ───────
    _all_schedules = db_get('schedules')
    if not isinstance(_all_schedules, list):
        _all_schedules = []

    _sched_schools = []
    for _sr in _all_schedules:
        if not isinstance(_sr, dict):
            continue
        # 선택 월 일정만
        if not str(_sr.get('month', '')).startswith(_sel_month):
            continue
        # 기사 매칭
        _sr_driver = str(_sr.get('driver', '')).strip()
        if _sr_driver and _sr_driver != driver_name:
            continue
        # 선택 요일 포함 여부
        try:
            _sr_weekdays = json.loads(_sr['weekdays']) \
                if isinstance(_sr.get('weekdays'), str) \
                else (_sr.get('weekdays') or [])
        except Exception:
            _sr_weekdays = []
        if _sel_weekday not in _sr_weekdays:
            continue
        # 학교 목록 추출
        try:
            _sr_schools = json.loads(_sr['schools']) \
                if isinstance(_sr.get('schools'), str) \
                else (_sr.get('schools') or [])
        except Exception:
            _sr_schools = []
        # 품목 추출
        try:
            _sr_items = json.loads(_sr['items']) \
                if isinstance(_sr.get('items'), str) \
                else (_sr.get('items') or [])
        except Exception:
            _sr_items = []

        for _sch in _sr_schools:
            _sched_schools.append({
                '학교명':   _sch,
                '수거품목': ', '.join(_sr_items) if _sr_items else '-',
                '담당업체': _sr.get('vendor', '-'),
                '등록구분': '본사' if _sr.get('registered_by', 'admin') == 'admin' else '외주업체',
                '_items':   _sr_items,   # 수거일지 입력 연동용 (표시 안 함)
            })

    # ── 일정 결과 표시 ──────────────────────────
    if not _sched_schools:
        st.info(f"{_sel_date} ({_sel_weekday}요일) 수거 일정이 없습니다.")
    else:
        st.success(f"총 {len(_sched_schools)}개 거래처 수거 예정")
        _display_df = pd.DataFrame([
            {k: v for k, v in s.items() if not k.startswith('_')}
            for s in _sched_schools
        ])
        st.dataframe(_display_df, use_container_width=True, hide_index=True)

    # ★ 조회된 학교 목록을 session_state에 저장 → 수거 입력에서 연동
    st.session_state["drv_today_schools"] = _sched_schools

    st.divider()

    # ── 수거일지 입력 (일정 연동) ─────────────────
    # 학교 목록: 일정에서 조회된 전체 학교 (중복 제거, 순서 유지)
    _linked_schools = st.session_state.get("drv_today_schools", [])
    schools = list(dict.fromkeys(
        s['학교명'] for s in _linked_schools if s.get('학교명')
    ))

    # 학교별 일정 품목 매핑 (수거 입력 시 품목 자동 표시용)
    _school_items_map = {}
    for _ls in _linked_schools:
        _sn = _ls.get('학교명', '')
        if _sn and _sn not in _school_items_map:
            _school_items_map[_sn] = _ls.get('_items', [])

    # ── 거래처 정보 매핑 (cust_type, addr) ──────────
    _cust_info_map = {}  # {거래처명: {cust_type, addr}}
    _cust_rows = db_get('customer_info', {'vendor': vendor})
    if isinstance(_cust_rows, list):
        for _cr in _cust_rows:
            _cname = _cr.get('name', '')
            if _cname:
                _cust_info_map[_cname] = {
                    'cust_type': _cr.get('cust_type', '학교'),
                    'addr': _cr.get('addr', ''),
                }
    _CUST_ICON = {
        '학교': '🏫', '기업': '🏢', '관공서': '🏛️',
        '일반업장': '🍽️', '기타': '📦',
    }

    if not schools:
        st.warning("담당 거래처가 없습니다. 관리자에게 문의하세요.")
    else:
        # 선택일 기준 완료 거래처 확인
        _sel_date_str = _sel_date.strftime('%Y-%m-%d')
        today_all  = [r for r in db_get('real_collection')
                      if r.get('driver') == driver_name
                      and str(r.get('collect_date', '')) == _sel_date_str]
        done_schools = {r.get('school_name') for r in today_all
                        if r.get('status') in ('submitted', 'confirmed')}

        # 요약 카드
        _total_cnt  = len(schools)
        _done_cnt   = len([s for s in schools if s in done_schools])
        _remain_cnt = max(0, _total_cnt - _done_cnt)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("담당 거래처", f"{_total_cnt}개")
        with c2:
            st.metric("완료", f"{_done_cnt}개")
        with c3:
            st.metric("남은 거래처", f"{_remain_cnt}개")
        _ratio = (_done_cnt / _total_cnt) if _total_cnt > 0 else 0.0
        _ratio = max(0.0, min(1.0, _ratio))
        st.progress(_ratio)

        st.divider()

        # ── 음성 입력 (전체 거래처 대상 · 자동 매칭) ─────────
        with st.expander("🎤 음성으로 수거량 입력 (자동 등록)", expanded=False):
            st.caption("예: \"안산고등학교 음식물 200\" → 자동 매칭 → 확인 팝업 → 등록 완료")
            _render_voice_input(schools, "drv")

        # 활성 거래처 (자동 스크롤용)
        _active_school = st.session_state.get("drv_active_school", "")

        # 거래처별 카드
        for school in schools:
            done   = school in done_schools

            # 거래처 구분 정보
            _ci = _cust_info_map.get(school, {})
            _ctype = _ci.get('cust_type', '학교')
            _caddr = _ci.get('addr', '')
            _cicon = _CUST_ICON.get(_ctype, '📦')

            color  = "#34a853" if done else "#ea4335"
            status = "✅ 완료"  if done else "⏳ 대기"

            # 내비: 주소가 있으면 주소로, 없으면 이름으로 검색
            _nav_query = _caddr if _caddr else school
            encoded = urllib.parse.quote(_nav_query)
            kakao   = f"https://map.kakao.com/link/search/{encoded}"
            tmap    = f"tmap://search?name={encoded}"
            naver   = f"https://map.naver.com/v5/search/{encoded}"

            # 카드 표시 (아이콘 + 구분 + 주소)
            _addr_line = (
                f'<div style="font-size:12px;color:#666;margin-top:4px;">'
                f'📍 {_caddr}</div>'
            ) if _caddr else ''
            st.markdown(f"""
            <div style="background:#f8f9fa;border-radius:10px;padding:14px;
                        margin-bottom:6px;border-left:5px solid {color};">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:700;font-size:15px;">{_cicon} {school}
                      <span style="font-size:11px;color:#888;font-weight:400;">({_ctype})</span>
                    </span>
                    <span style="color:{color};font-weight:700;">{status}</span>
                </div>
                {_addr_line}
            </div>
            """, unsafe_allow_html=True)

            if not done:
                # 내비 버튼
                n1, n2, n3 = st.columns(3)
                with n1:
                    st.markdown(
                        f'<a href="{kakao}" target="_blank" style="display:block;text-align:center;'
                        f'background:#FEE500;color:#000;padding:8px;border-radius:8px;'
                        f'text-decoration:none;font-size:13px;font-weight:700;">🗺️ 카카오맵</a>',
                        unsafe_allow_html=True)
                with n2:
                    st.markdown(
                        f'<a href="{tmap}" target="_blank" style="display:block;text-align:center;'
                        f'background:#0064FF;color:#fff;padding:8px;border-radius:8px;'
                        f'text-decoration:none;font-size:13px;font-weight:700;">🚗 티맵</a>',
                        unsafe_allow_html=True)
                with n3:
                    st.markdown(
                        f'<a href="{naver}" target="_blank" style="display:block;text-align:center;'
                        f'background:#03C75A;color:#fff;padding:8px;border-radius:8px;'
                        f'text-decoration:none;font-size:13px;font-weight:700;">🟢 네이버지도</a>',
                        unsafe_allow_html=True)

                # 수거 입력 (인라인 expander)
                _is_active = (_active_school == school)
                with st.expander(f"{_cicon} {school} 수거량 입력", expanded=_is_active):

                    # 일정 연동 품목 안내
                    _linked_items = _school_items_map.get(school, [])
                    if _linked_items:
                        st.caption(f"📋 등록 품목: {', '.join(_linked_items)}")

                    # 현장 증빙 사진
                    with st.expander("📸 현장 증빙 사진 (선택)", expanded=False):
                        photo = st.file_uploader(
                            "사진 촬영 또는 갤러리에서 선택",
                            type=['jpg', 'jpeg', 'png'],
                            key=f"drv_photo_{school}",
                            help="모바일: 촬영 또는 갤러리 선택 가능"
                        )
                        if photo:
                            st.image(photo, caption="첨부된 사진", use_container_width=True)
                            st.success("📸 사진이 첨부되었습니다.")

                    # ── 날짜별 다중행 수거량 입력 ──────────────────
                    _dr_key = f"drv_date_rows_{school}"
                    # 일정 탭에서 선택한 날짜를 기본값으로 사용
                    _init_date = st.session_state.get("drv_schedule_date", today)
                    _init_item = _linked_items[0] if _linked_items else "음식물"
                    if _dr_key not in st.session_state:
                        st.session_state[_dr_key] = [
                            {"date": _init_date, "weight": 0.0, "item": _init_item}
                        ]

                    st.caption("📆 날짜별 수거량 입력 (여러 날짜 입력 가능)")
                    _items_list = ["음식물", "재활용", "일반"]

                    # 키패드 상태 키
                    _np_tgt_key = f"_np_target_{school}"
                    _np_buf_key = f"_np_buf_{school}"
                    if _np_tgt_key not in st.session_state:
                        st.session_state[_np_tgt_key] = -1

                    for _idx, _row in enumerate(st.session_state[_dr_key]):
                        _rc1, _rc2, _rc3, _rc4 = st.columns([3, 2, 2, 1])
                        with _rc1:
                            _new_date = st.date_input(
                                "수거일" if _idx == 0 else f"수거일 {_idx+1}",
                                value=_row["date"],
                                key=f"drv_dr_date_{school}_{_idx}"
                            )
                            st.session_state[_dr_key][_idx]["date"] = _new_date
                        with _rc2:
                            # 수거량: 키패드 열기 버튼
                            _wt_label = "수거량(kg)" if _idx == 0 else f"수거량 {_idx+1}"
                            _wt_display = f"{_row['weight']:.1f}" if _row["weight"] > 0 else "0"
                            _is_editing = (st.session_state.get(_np_tgt_key, -1) == _idx)
                            st.markdown(f"<div style='font-size:12px;color:#666;margin-bottom:2px'>{_wt_label}</div>",
                                        unsafe_allow_html=True)
                            _btn_label = f"✏️ {_wt_display} kg" if not _is_editing else f"📝 입력중..."
                            if st.button(_btn_label, key=f"drv_dr_wt_{school}_{_idx}",
                                         use_container_width=True):
                                if _is_editing:
                                    st.session_state[_np_tgt_key] = -1
                                else:
                                    st.session_state[_np_tgt_key] = _idx
                                    st.session_state[_np_buf_key] = f"{_row['weight']:.1f}" if _row["weight"] > 0 else ""
                                st.rerun()
                        with _rc3:
                            _item_idx = _items_list.index(_row["item"]) if _row["item"] in _items_list else 0
                            _new_item = st.selectbox(
                                "품목" if _idx == 0 else f"품목 {_idx+1}",
                                _items_list, index=_item_idx,
                                key=f"drv_dr_item_{school}_{_idx}"
                            )
                            st.session_state[_dr_key][_idx]["item"] = _new_item
                        with _rc4:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if len(st.session_state[_dr_key]) > 1 and _idx > 0:
                                if st.button("🗑️", key=f"drv_dr_del_{school}_{_idx}"):
                                    st.session_state[_dr_key].pop(_idx)
                                    st.rerun()

                    # ── 숫자 키패드 (전체 너비) ────────────────────
                    _render_numpad(_dr_key, school)

                    # 날짜 추가 버튼
                    if st.button("＋ 날짜 추가", key=f"drv_dr_add_{school}"):
                        _yesterday = today - timedelta(days=1)
                        _existing_dates = [r["date"] for r in st.session_state[_dr_key]]
                        if _yesterday in _existing_dates:
                            st.warning("⚠️ 이미 추가된 날짜입니다")
                        else:
                            st.session_state[_dr_key].append(
                                {"date": _yesterday, "weight": 0.0, "item": "음식물"}
                            )
                            st.rerun()

                    # ── 공통 필드 (기존 유지) ─────────────────────
                    _fc1, _fc2 = st.columns(2)
                    with _fc1:
                        unit_price   = st.number_input("단가 (원)", min_value=0, step=1,
                                                        key=f"drv_price_{school}")
                    with _fc2:
                        collect_time = st.text_input(
                            "수거 시간",
                            value=datetime.now(ZoneInfo('Asia/Seoul')).strftime("%H:%M"),
                            key=f"drv_time_{school}"
                        )

                    memo = st.text_area("메모", placeholder="특이사항 입력...",
                                        height=70, key=f"drv_memo_{school}")

                    # 합계 미리보기
                    _total_wt = sum(r["weight"] for r in st.session_state[_dr_key])
                    if _total_wt > 0:
                        st.info(f"📊 총 {len(st.session_state[_dr_key])}건, 합계 **{_total_wt:.1f}kg**"
                                + (f" × {unit_price:,}원 = **{_total_wt*unit_price:,.0f}원**" if unit_price > 0 else ""))

                    # ── 저장 버튼 (행별 반복 저장) ────────────────
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("📋 임시저장", use_container_width=True,
                                     key=f"btn_draft_{school}"):
                            _saved = 0
                            for _row in st.session_state[_dr_key]:
                                if _row["weight"] <= 0:
                                    continue
                                row_id = _save(vendor, school, _row["date"], collect_time,
                                               _row["item"], _row["weight"], unit_price,
                                               driver_name, memo, 'draft')
                                if row_id:
                                    _saved += 1
                            if _saved > 0:
                                st.success(f"임시저장 완료 ({_saved}건)")
                                st.session_state[_dr_key] = [
                                    {"date": today, "weight": 0.0, "item": "음식물"}
                                ]
                            else:
                                st.error("저장할 데이터가 없습니다 (수거량 0 제외)")

                    with b2:
                        if st.button("✅ 수거완료 · 본사전송", type="primary",
                                     use_container_width=True, key=f"btn_submit_{school}"):
                            _saved = 0
                            for _row in st.session_state[_dr_key]:
                                if _row["weight"] <= 0:
                                    continue
                                row_id = _save(vendor, school, _row["date"], collect_time,
                                               _row["item"], _row["weight"], unit_price,
                                               driver_name, memo, 'submitted')
                                if row_id:
                                    _saved += 1
                            if _saved > 0:
                                st.success(f"✅ 본사 전송 완료! ({_saved}건)")
                                st.session_state[_dr_key] = [
                                    {"date": today, "weight": 0.0, "item": "음식물"}
                                ]
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("전송할 데이터가 없습니다 (수거량 0 제외)")

        # 오늘 입력 현황
        st.divider()
        st.markdown("#### 📋 오늘 입력 현황")
        if not today_all:
            st.info("오늘 입력된 수거 실적이 없습니다.")
        else:
            df = pd.DataFrame(today_all)
            if 'status' in df.columns:
                df['status'] = df['status'].map({
                    'draft':     '📋 임시저장',
                    'submitted': '✅ 전송완료',
                }).fillna(df['status'])
            show = [c for c in ['school_name','item_type','weight','status','memo']
                    if c in df.columns]
            st.dataframe(df[show], use_container_width=True, hide_index=True)
            m1, m2 = st.columns(2)
            with m1:
                st.metric("오늘 수거량", f"{df['weight'].sum():,.1f} kg")
            with m2:
                submitted = len([r for r in today_all if r.get('status') == 'submitted'])
                st.metric("전송 완료", f"{submitted}건")

    st.divider()

    # ══════════════════════════════════════════════
    # 섹션3: 퇴근
    # ══════════════════════════════════════════════
    st.markdown("### 🏠 퇴근")

    today_done_all = [r for r in db_get('real_collection')
                      if r.get('driver') == driver_name
                      and str(r.get('collect_date', '')) == today_str]
    submitted_cnt = len([r for r in today_done_all if r.get('status') == 'submitted'])
    total_weight  = sum(float(r.get('weight', 0)) for r in today_done_all)
    all_schools   = get_schools_by_vendor(vendor)
    done_schools2 = {r.get('school_name') for r in today_done_all
                     if r.get('status') == 'submitted'}

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("전송 완료", f"{submitted_cnt}건")
    with c2:
        st.metric("총 수거량", f"{total_weight:,.1f} kg")
    with c3:
        st.metric("거래처 완료율", f"{len(done_schools2)}/{len(all_schools)}개")

    remain = [s for s in all_schools if s not in done_schools2]
    if remain:
        st.warning(f"⚠️ 미완료 거래처 {len(remain)}곳: {', '.join(remain)}")

    safety_done = all(
        st.session_state.get(key, False) for key, _ in SAFETY_CHECKS
    )
    if not safety_done:
        st.warning("⚠️ 안전점검이 완료되지 않았습니다. 위 안전점검 섹션을 확인하세요.")

    if st.button("🏠 퇴근하기", use_container_width=True,
                 type="primary", key="btn_off"):
        now_time = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%H시 %M분')
        st.balloons()
        st.success(f"✅ {driver_name}님, {now_time} 퇴근 처리 완료! 수고하셨습니다. 🎉")
        st.caption("퇴근 기록이 본사에 자동 전송됩니다.")


# ── 내부 유틸 ──────────────────────────────────────
def _validate(school, weight):
    if not school:
        st.error("학교를 선택하세요.")
        return False
    if weight <= 0:
        st.error("수거량을 입력하세요.")
        return False
    return True


def _save(vendor, school, collect_date, collect_time,
          item_type, weight, unit_price, driver, memo, status):
    now = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
    return db_insert('real_collection', {
        'vendor':       vendor,
        'school_name':  school,
        'collect_date': str(collect_date),
        'collect_time': collect_time,
        'item_type':    item_type,
        'weight':       weight,
        'unit_price':   unit_price,
        'amount':       weight * unit_price,
        'driver':       driver,
        'memo':         memo,
        'status':       status,
        'submitted_at': now if status == 'submitted' else '',
        'created_at':   now,
    })
