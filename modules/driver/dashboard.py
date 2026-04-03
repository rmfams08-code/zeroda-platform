# modules/driver/dashboard.py
# 기사 전용 앱 - 단일 화면 (안전점검 → 수거일정 → 퇴근)
import streamlit as st
import pandas as pd
import urllib.parse
import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from database.db_manager import db_insert, db_get, db_upsert, get_schools_by_vendor, save_customer_gps
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

def _render_voice_input(schools: list, school_key_prefix: str,
                        cust_gps_map: dict = None):
    """
    마이크 버튼 → 음성 인식 → '거래처명 품목 수거량' 파싱
    → confirm 팝업 → 확인 시 postMessage 로 부모에 전달
    → 숨겨진 리스너 컴포넌트가 session_state 에 저장 → 자동 입력
    cust_gps_map: {거래처명: {cust_type, lat, lng}} — GPS 근접 매칭용
    """
    _schools_js = json.dumps(schools, ensure_ascii=False)
    # GPS 좌표 + 구분 데이터를 JS로 전달
    _gps_data = {}
    if cust_gps_map:
        for name, info in cust_gps_map.items():
            _gps_data[name] = {
                'type': info.get('cust_type', '학교'),
                'lat': info.get('lat', 0),
                'lng': info.get('lng', 0),
            }
    _gps_js = json.dumps(_gps_data, ensure_ascii=False)

    # ── (A) 숨겨진 text_input 브릿지 (JS→Python 통신용) ──
    _bridge_key = f"{school_key_prefix}_voice_bridge"
    _gps_bridge_key = f"{school_key_prefix}_gps_bridge"
    # :has() 셀렉터로 Streamlit 컨테이너째 완전히 숨김
    st.markdown("""<style>
    div[data-testid="stTextInput"]:has(input[aria-label="_vc_data_"]),
    div[data-testid="stTextInput"]:has(input[aria-label="_gps_data_"]) {
      position:absolute !important; left:-9999px !important;
      height:0 !important; overflow:hidden !important;
      margin:0 !important; padding:0 !important; opacity:0 !important;
    }
    </style>""", unsafe_allow_html=True)
    st.text_input("_vc_data_", value="", key=_bridge_key, label_visibility="collapsed")
    st.text_input("_gps_data_", value="", key=_gps_bridge_key, label_visibility="collapsed")

    # ── (B) 음성인식 + confirm 팝업 컴포넌트 ──
    import time as _time
    _render_id = int(_time.time() * 1000)  # 매 rerun마다 변경 → iframe 강제 재생성
    _html = f"""
    <!-- render_id={_render_id} -->
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
    const gpsData = {_gps_js};
    const itemKeywords = {{
      '음식물': ['음식물', '음식', '잔반', '급식'],
      '재활용': ['재활용', '분리수거', '페트', '캔'],
      '일반':   ['일반', '종량제', '생활']
    }};
    // 키워드 → 거래처 구분 매핑 (GPS 근접 검색용)
    const typeKeywords = {{
      '학교': ['학교', '초등학교', '중학교', '고등학교', '초등', '중등', '고등'],
      '기업': ['기업', '회사', '공장', '사무실', '오피스'],
      '관공서': ['관공서', '구청', '시청', '주민센터', '동사무소', '관청'],
      '일반업장': ['식당', '마트', '백화점', '매장', '업장', '가게', '편의점', '카페']
    }};
    let recognition = null;
    let currentGPS = null;  // {{lat, lng}} 현재 위치

    // ── Haversine 거리 계산 (미터 단위) ──
    function haversine(lat1, lng1, lat2, lng2) {{
      const R = 6371000;
      const toRad = x => x * Math.PI / 180;
      const dLat = toRad(lat2 - lat1);
      const dLng = toRad(lng2 - lng1);
      const a = Math.sin(dLat/2)**2
              + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2))
              * Math.sin(dLng/2)**2;
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }}

    // ── GPS 기반 근접 거래처 검색 ──
    function findNearbyByKeyword(text) {{
      if (!currentGPS) return null;
      // 텍스트에서 구분 키워드 감지
      let matchedType = null;
      for (const [ctype, keywords] of Object.entries(typeKeywords)) {{
        for (const kw of keywords) {{
          if (text.includes(kw)) {{ matchedType = ctype; break; }}
        }}
        if (matchedType) break;
      }}
      if (!matchedType) return null;

      // 해당 구분 + GPS 좌표 있는 거래처 → 거리 계산
      const candidates = [];
      let totalOfType = 0;   // 해당 타입의 전체 거래처 수
      let noGpsCount = 0;    // GPS 미등록 거래처 수
      for (const [name, info] of Object.entries(gpsData)) {{
        if (info.type === matchedType) {{
          totalOfType++;
          if (info.lat === 0 && info.lng === 0) {{
            noGpsCount++;
          }} else {{
            const dist = haversine(currentGPS.lat, currentGPS.lng, info.lat, info.lng);
            candidates.push({{ name, dist, type: info.type }});
          }}
        }}
      }}
      if (candidates.length === 0) {{
        // GPS 미등록 원인 정보를 포함하여 반환
        if (noGpsCount > 0) {{
          return {{ candidates: [], keyword: matchedType, noGps: true, noGpsCount: noGpsCount }};
        }}
        return null;
      }}

      // 거리순 정렬
      candidates.sort((a, b) => a.dist - b.dist);

      // 100m 이내 → 200m → 300m 자동 확장
      for (const radius of [100, 200, 300]) {{
        const nearby = candidates.filter(c => c.dist <= radius);
        if (nearby.length > 0) {{
          return {{ candidates: nearby, radius, keyword: matchedType }};
        }}
      }}
      // 300m 초과 시 가장 가까운 1개라도 반환 (확인 필요)
      if (candidates[0].dist <= 1000) {{
        return {{ candidates: [candidates[0]], radius: Math.round(candidates[0].dist), keyword: matchedType }};
      }}
      return null;
    }}

    // ── GPS 획득 (음성 시작 시 자동 실행) ──
    function acquireGPS() {{
      if (navigator.geolocation) {{
        navigator.geolocation.getCurrentPosition(
          function(pos) {{
            currentGPS = {{ lat: pos.coords.latitude, lng: pos.coords.longitude }};
          }},
          function(err) {{ currentGPS = null; }},
          {{ enableHighAccuracy: true, timeout: 5000, maximumAge: 30000 }}
        );
      }}
    }}
    // 페이지 로드 시 GPS 미리 획득
    acquireGPS();

    // ── 유사도 계산 (Levenshtein → 0~1 비율) ──
    function levenshtein(a, b) {{
      const m = a.length, n = b.length;
      if (m === 0) return n;
      if (n === 0) return m;
      const d = Array.from({{length: m+1}}, (_, i) => [i]);
      for (let j = 1; j <= n; j++) d[0][j] = j;
      for (let i = 1; i <= m; i++) {{
        for (let j = 1; j <= n; j++) {{
          const cost = a[i-1] === b[j-1] ? 0 : 1;
          d[i][j] = Math.min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+cost);
        }}
      }}
      return d[m][n];
    }}
    function similarity(a, b) {{
      const maxLen = Math.max(a.length, b.length);
      if (maxLen === 0) return 1.0;
      return 1.0 - levenshtein(a, b) / maxLen;
    }}

    // ── 한글 초성 추출 (ㄱ~ㅎ) ──
    function getChosung(str) {{
      const CHO = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ',
                   'ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ'];
      let result = '';
      for (const ch of str) {{
        const code = ch.charCodeAt(0) - 0xAC00;
        if (code >= 0 && code <= 11171) {{
          result += CHO[Math.floor(code / 588)];
        }} else {{
          result += ch;
        }}
      }}
      return result;
    }}

    function findSchool(text) {{
      // 1단계: 정확 매칭 (기존)
      let best = null, bestLen = 0;
      for (const s of schools) {{
        if (text.includes(s) && s.length > bestLen) {{
          best = s;
          bestLen = s.length;
        }}
      }}
      if (best) return {{ name: best, confidence: 1.0, method: 'exact' }};

      // 2단계: 단축명 매칭 — "송호고"→"송호고등학교", "송호초등"→"송호초등학교" 등
      // 2-a: 음성 텍스트에서 약칭 패턴 추출 → 풀네임 확장 (긴 suffix 우선)
      const shortPatterns = [
        {{ suffix: '고등', expand: ['고등학교'], lookahead: '(?!학)' }},
        {{ suffix: '초등', expand: ['초등학교'], lookahead: '(?!학)' }},
        {{ suffix: '고',   expand: ['고등학교'], lookahead: '(?!등|학)' }},
        {{ suffix: '중',   expand: ['중학교'],   lookahead: '(?!등|학)' }},
        {{ suffix: '초',   expand: ['초등학교'], lookahead: '(?!등|학)' }},
      ];
      for (const sp of shortPatterns) {{
        const re = new RegExp('([가-힣]{{2,6}})' + sp.suffix + sp.lookahead, 'g');
        let m;
        while ((m = re.exec(text)) !== null) {{
          const stem = m[1];  // 예: "송호"
          for (const s of schools) {{
            for (const ex of sp.expand) {{
              if (s === stem + ex) {{
                return {{ name: s, confidence: 0.97, method: 'short_expand' }};
              }}
            }}
          }}
        }}
      }}

      // 2-b: 접미사 제거 후 포함 매칭 (긴 패턴 우선 제거 + 3자 이상만 허용)
      for (const s of schools) {{
        const short = s.replace(/초등학교|고등학교|중학교|학교/g, '');
        if (short.length >= 3 && text.includes(short) && short.length > bestLen) {{
          best = s;
          bestLen = short.length;
        }}
      }}
      if (best) return {{ name: best, confidence: 0.95, method: 'short' }};

      // 3단계: Fuzzy Matching — STT 오인식 대응
      // 음성 텍스트에서 학교명 후보 추출 (숫자/품목/단독타입 키워드 제거)
      let cleaned = text
        .replace(/\\d+/g, '')
        .replace(/음식물|음식|잔반|급식|재활용|분리수거|페트|캔|일반|종량제|생활/g, '')
        .replace(/킬로|키로|kg/gi, '')
        .replace(/학교|기업|회사|공장|관공서|구청|시청|주민센터|동사무소|식당|마트|백화점|업장|가게|편의점|카페/g, '')
        .trim();

      // cleaned가 2자 미만이면 Fuzzy 스킵 → GPS 근접 검색으로 자연 전환
      if (cleaned.length < 2) return null;

      let bestFuzzy = null, bestScore = 0;
      for (const s of schools) {{
        // 전체 이름 vs 정제된 텍스트
        const score1 = similarity(cleaned, s);
        // 접미사 제거 비교 (긴 패턴 우선)
        const short = s.replace(/초등학교|고등학교|중학교|학교/, '');
        const cleanedShort = cleaned.replace(/초등학교|고등학교|중학교|학교/g, '');
        const score2 = short.length >= 2 ? similarity(cleanedShort, short) : 0;
        // 초성 비교 (보조)
        const score3 = similarity(getChosung(cleaned), getChosung(s)) * 0.9;
        const maxScore = Math.max(score1, score2, score3);
        if (maxScore > bestScore) {{
          bestScore = maxScore;
          bestFuzzy = s;
        }}
      }}

      if (bestFuzzy && bestScore >= 0.80) {{
        return {{ name: bestFuzzy, confidence: bestScore, method: 'fuzzy_auto' }};
      }}
      if (bestFuzzy && bestScore >= 0.55) {{
        return {{ name: bestFuzzy, confidence: bestScore, method: 'fuzzy_confirm' }};
      }}
      return null;
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

    // ── GPS 키워드 우선 감지: 구체적 학교명 없이 타입 키워드만 있는지 판별 ──
    function checkTypeKeywordOnly(text) {{
      // 숫자, 품목 키워드, 단위 제거
      let rest = text
        .replace(/\\d+\\.?\\d*/g, '')
        .replace(/음식물|음식|잔반|급식|재활용|분리수거|페트|캔|일반|종량제|생활/g, '')
        .replace(/킬로|키로|kg/gi, '')
        .replace(/\\s+/g, '')
        .trim();
      if (rest.length === 0) return false;
      // typeKeywords의 모든 키워드 제거
      const allTypeKw = ['초등학교','고등학교','중학교','학교','초등','중등','고등',
        '기업','회사','공장','사무실','오피스',
        '관공서','구청','시청','주민센터','동사무소','관청',
        '식당','마트','백화점','매장','업장','가게','편의점','카페'];
      for (const kw of allTypeKw) {{
        rest = rest.split(kw).join('');
      }}
      rest = rest.trim();
      // 남은 한글이 1자 이하면 → 타입 키워드만 있었다고 판단
      const hangul = rest.replace(/[^가-힣]/g, '');
      return hangul.length <= 1;
    }}

    // ── 부모 DOM의 숨겨진 input에 값 설정 → Streamlit rerun 유발 ──
    function setBridgeValue(ariaLabel, jsonStr) {{
      try {{
        const doc = window.parent.document;
        const inp = doc.querySelector('input[aria-label="' + ariaLabel + '"]');
        if (!inp) {{
          console.error('Bridge input not found:', ariaLabel);
          return false;
        }}
        // 1. 포커스
        inp.focus();
        // 2. React native value setter
        const nativeSetter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype, 'value'
        ).set;
        nativeSetter.call(inp, jsonStr);
        // 3. React 내부 onChange 핸들러 직접 호출
        const reactKey = Object.keys(inp).find(function(k) {{
          return k.startsWith('__reactProps$');
        }});
        if (reactKey && inp[reactKey] && inp[reactKey].onChange) {{
          inp[reactKey].onChange({{ target: inp }});
        }}
        // 4. 네이티브 이벤트 (백업)
        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
        // 5. Enter 키 시뮬레이션 → Streamlit text_input 값 커밋
        setTimeout(function() {{
          inp.dispatchEvent(new KeyboardEvent('keydown', {{
            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
          }}));
          inp.dispatchEvent(new KeyboardEvent('keypress', {{
            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
          }}));
          inp.dispatchEvent(new KeyboardEvent('keyup', {{
            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
          }}));
        }}, 50);
        // 6. blur → 최종 커밋 보장
        setTimeout(function() {{
          inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
          inp.blur();
        }}, 200);
        return true;
      }} catch(ex) {{
        console.error('setBridgeValue error:', ex);
        return false;
      }}
    }}

    function applyVoiceResult(school, item, weight) {{
      const el   = document.getElementById('mic-result');
      const btn  = document.getElementById('mic-btn');
      btn.disabled = true;

      // ── 카운트 타이머 + 프로그레스바 ──
      let sec = 0;
      const MAX_SEC = 3;
      function updateUI() {{
        sec++;
        const pct = Math.min(100, Math.round((sec / MAX_SEC) * 100));
        el.innerHTML =
          '<div style="text-align:center">'
          + '<div style="font-size:17px;color:#1a73e8;font-weight:700;margin-bottom:6px;">'
          + '⏳ ' + school + ' / ' + item + ' / ' + weight + 'kg'
          + '</div>'
          + '<div style="background:#e0e0e0;border-radius:8px;height:10px;'
          + 'width:100%;max-width:320px;margin:0 auto 6px;">'
          + '<div style="background:linear-gradient(90deg,#1a73e8,#34a853);'
          + 'height:100%;border-radius:8px;width:' + pct + '%;'
          + 'transition:width 0.3s ease;"></div></div>'
          + '<div style="font-size:14px;color:#666;">전송 중... '
          + '<b>' + sec + '초</b></div></div>';
        btn.textContent = '⏳ 전송 중... ' + sec + '초';
      }}
      updateUI();
      const timer = setInterval(updateUI, 1000);

      // 숨겨진 input에 JSON 전달 → Streamlit rerun → Python에서 DB 저장
      const data = JSON.stringify({{s: school, i: item, w: weight}});
      const ok = setBridgeValue('_vc_data_', data);
      if (ok) {{
        setTimeout(function() {{ clearInterval(timer); }}, 3000);
      }} else {{
        clearInterval(timer);
        el.innerHTML = '<div style="color:#ea4335;font-weight:700;">⚠️ 전송 실패 — 다시 시도해주세요</div>';
        btn.disabled = false;
        btn.textContent = '🎤 다시 입력하기';
      }}
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
          // GPS 선택 후 수거량만 말한 경우 (예: "음식물 200")
          if (window._gps_selected) {{
            const w = findWeight(final_text);
            const it = findItem(final_text);
            if (w !== null && w > 0) {{
              const gs = window._gps_selected;
              result.innerHTML = '📍 <b>' + gs + '</b> / 📦 <b>' + it + '</b> / ⚖️ <b>' + w + 'kg</b>';
              window._gps_selected = null;
              setTimeout(function() {{
                const ok = confirm(gs + ' / ' + it + ' / ' + w + 'kg\\n\\n수거 등록하시겠습니까?');
                if (ok) {{ applyVoiceResult(gs, it, w); }}
                else {{ status.textContent = '❌ 취소됨'; }}
              }}, 200);
              return;
            }}
          }}

          const weight = findWeight(final_text);
          const item   = findItem(final_text);

          // ── GPS 키워드 우선 감지: "학교", "기업" 등 단독 키워드면 GPS 직행 ──
          const isTypeOnly = checkTypeKeywordOnly(final_text);
          const match = isTypeOnly ? null : findSchool(final_text);

          if (match && weight !== null && weight > 0) {{
            const school = match.name;
            const conf = match.confidence;
            const method = match.method;

            // fuzzy_confirm(55~80%): 추천 확인 팝업
            if (method === 'fuzzy_confirm') {{
              const pct = Math.round(conf * 100);
              result.innerHTML = '🗣️ "' + final_text + '"<br>'
                + '🔍 유사 매칭: <b>' + school + '</b> (유사도 ' + pct + '%)';

              setTimeout(function() {{
                const ok = confirm(
                  '인식: "' + final_text + '"\\n\\n'
                  + '혹시 "' + school + '" 맞으십니까? (유사도 ' + pct + '%)\\n\\n'
                  + '확인 → 등록 / 취소 → 다시 말하기'
                );
                if (ok) {{
                  // 확인 후 등록 진행
                  const ok2 = confirm(
                    school + ' / ' + item + ' / ' + weight + 'kg\\n\\n'
                    + '수거 등록하시겠습니까?'
                  );
                  if (ok2) {{
                    applyVoiceResult(school, item, weight);
                  }} else {{
                    status.textContent = '❌ 취소됨 — 다시 말씀해 주세요';
                  }}
                }} else {{
                  status.textContent = '🎤 다시 말씀해 주세요';
                }}
              }}, 200);
            }} else {{
              // exact / short / fuzzy_auto(80%+): 바로 등록 확인
              let matchLabel = '';
              if (method === 'fuzzy_auto') {{
                matchLabel = ' (자동매칭 ' + Math.round(conf * 100) + '%)';
              }}
              result.innerHTML = '🗣️ "' + final_text + '"<br>'
                + '📍 <b>' + school + '</b>' + matchLabel + ' / '
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
            }}
          }} else {{
            // ── GPS 근접 매칭 시도 (이름 매칭 실패 시) ──
            const nearby = findNearbyByKeyword(final_text);
            const weight2 = weight || findWeight(final_text);
            const item2   = item || findItem(final_text);

            if (nearby && nearby.candidates.length > 0) {{
              // GPS 근접 거래처 발견
              if (nearby.candidates.length === 1) {{
                // 1개: 바로 확인
                const c = nearby.candidates[0];
                const distTxt = c.dist < 1000 ? Math.round(c.dist) + 'm' : (c.dist/1000).toFixed(1) + 'km';
                result.innerHTML = '🗣️ "' + final_text + '"<br>'
                  + '📍 GPS 매칭: <b>' + c.name + '</b> (' + distTxt + ')';

                setTimeout(function() {{
                  if (weight2 !== null && weight2 > 0) {{
                    const ok = confirm(
                      '📍 ' + c.name + ' (' + distTxt + ')\\n'
                      + '📦 ' + item2 + ' / ⚖️ ' + weight2 + 'kg\\n\\n'
                      + '수거 등록하시겠습니까?'
                    );
                    if (ok) {{ applyVoiceResult(c.name, item2, weight2); }}
                    else {{ status.textContent = '❌ 취소됨'; }}
                  }} else {{
                    // 수거량 없으면 거래처만 확인 후 수거량 재입력 안내
                    const ok = confirm(c.name + ' (' + distTxt + ')\\n\\n맞으십니까?');
                    if (ok) {{
                      status.textContent = '✅ ' + c.name + ' 선택됨 — 수거량을 말씀해 주세요 (예: "음식물 200")';
                      // 선택 기억
                      window._gps_selected = c.name;
                    }} else {{ status.textContent = '🎤 다시 말씀해 주세요'; }}
                  }}
                }}, 200);
              }} else {{
                // 2개+: 선택지 표시
                let list = nearby.candidates.slice(0, 4).map(function(c, i) {{
                  const d = c.dist < 1000 ? Math.round(c.dist) + 'm' : (c.dist/1000).toFixed(1) + 'km';
                  return (i+1) + '. ' + c.name + ' (' + d + ')';
                }}).join('\\n');

                setTimeout(function() {{
                  const pick = prompt(
                    '📍 반경 ' + nearby.radius + 'm 내 ' + nearby.keyword + ' ' + nearby.candidates.length + '곳 발견:\\n\\n'
                    + list + '\\n\\n번호를 입력하세요 (1~' + Math.min(4, nearby.candidates.length) + '):'
                  );
                  const idx = parseInt(pick) - 1;
                  if (idx >= 0 && idx < nearby.candidates.length) {{
                    const chosen = nearby.candidates[idx].name;
                    if (weight2 !== null && weight2 > 0) {{
                      applyVoiceResult(chosen, item2, weight2);
                    }} else {{
                      status.textContent = '✅ ' + chosen + ' 선택됨 — 수거량을 말씀해 주세요';
                      window._gps_selected = chosen;
                    }}
                  }} else {{
                    status.textContent = '❌ 취소됨 — 다시 말씀해 주세요';
                  }}
                }}, 200);
              }}
            }} else if (nearby && nearby.noGps) {{
              // GPS 좌표 미등록 거래처 안내
              let msg = '🗣️ "' + final_text + '"<br>';
              msg += '<span style="color:#e67700;font-weight:700;">📍 ' + nearby.keyword + ' '
                + nearby.noGpsCount + '곳의 GPS 좌표가 등록되지 않았습니다</span><br>';
              msg += '<span style="font-size:13px;color:#888;">거래처 카드에서 "📍 현재 위치 저장"을 먼저 해주세요</span>';
              result.innerHTML = msg;
            }} else {{
              // GPS 근접도 실패 — 기존 안내
              let msg = '🗣️ "' + final_text + '"<br>';
              if (!match) msg += '⚠️ 거래처 인식 실패&nbsp;&nbsp;';
              else msg += '📍 거래처: <b>' + match.name + '</b>&nbsp;&nbsp;';
              if (weight === null || weight <= 0) msg += '⚠️ 수거량 인식 실패';
              else msg += '⚖️ 수거량: <b>' + weight + 'kg</b>';
              if (!currentGPS) msg += '<br><span style="font-size:12px;color:#e67700;">📍 GPS 미획득 — 위치 권한을 확인해 주세요</span>';
              msg += '<br><span style="font-size:13px;color:#888;">다시 말씀해 주세요 (예: "강남중학교 음식물 200")</span>';
              result.innerHTML = msg;
            }}
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

    # ── 음성인식 자동입력 수신 처리 (session_state 브릿지 방식) ──
    _vb_val = st.session_state.get("drv_voice_bridge", "")
    if _vb_val and _vb_val.strip().startswith("{"):
        try:
            _vb = json.loads(_vb_val)
            _vc_school = _vb.get('s', '')
            _vc_weight = float(_vb.get('w', 0))
            _vc_item = _vb.get('i', '음식물')
        except (json.JSONDecodeError, ValueError, TypeError):
            _vc_school, _vc_weight, _vc_item = '', 0.0, '음식물'
        # 브릿지 즉시 초기화 (재진입 방지)
        st.session_state["drv_voice_bridge"] = ""
        if _vc_school and _vc_weight > 0:
            # ── 자동 본사전송: DB에 바로 submitted 상태로 저장 ──
            _vc_time = datetime.now(ZoneInfo('Asia/Seoul')).strftime("%H:%M")
            _vc_saved = _save(
                vendor, _vc_school, today, _vc_time,
                _vc_item, _vc_weight, 0, driver_name, '', 'submitted'
            )
            if _vc_saved:
                st.session_state["_voice_success"] = (
                    f"✅ 음성입력 → 본사전송 완료: {_vc_school} / {_vc_item} / {_vc_weight}kg"
                )
                # 다음 미완료 거래처로 자동 스크롤 설정
                _vc_all_schools = get_schools_by_vendor(vendor)
                _vc_done = {r.get('school_name') for r in db_get('real_collection')
                            if r.get('driver') == driver_name
                            and str(r.get('collect_date', '')) == today_str
                            and r.get('status') in ('submitted', 'confirmed')}
                _vc_done.add(_vc_school)  # 방금 전송한 것도 포함
                _vc_remain = [s for s in _vc_all_schools if s not in _vc_done]
                if _vc_remain:
                    st.session_state["drv_active_school"] = _vc_remain[0]
                else:
                    st.session_state["drv_active_school"] = ""
            else:
                st.session_state["_voice_success"] = (
                    f"⚠️ 음성입력 저장 실패: {_vc_school} / {_vc_item} / {_vc_weight}kg"
                )
            # 기존 session_state 행도 초기화 (중복 방지)
            _dr_key = f"drv_date_rows_{_vc_school}"
            st.session_state[_dr_key] = [
                {"date": today, "weight": 0.0, "item": _vc_item}
            ]

    # ── GPS 좌표 저장 수신 처리 (session_state 브릿지 방식) ──
    _gb_val = st.session_state.get("drv_gps_bridge", "")
    if _gb_val and _gb_val.strip().startswith("{"):
        try:
            _gb = json.loads(_gb_val)
            _gps_school = _gb.get('school', '')
            _gps_lat = float(_gb.get('lat', 0))
            _gps_lng = float(_gb.get('lng', 0))
        except (json.JSONDecodeError, ValueError, TypeError):
            _gps_school, _gps_lat, _gps_lng = '', 0, 0
        st.session_state["drv_gps_bridge"] = ""
        if _gps_school and _gps_lat != 0 and _gps_lng != 0:
            save_customer_gps(vendor, _gps_school, _gps_lat, _gps_lng)
            st.session_state["_voice_success"] = (
                f"📍 위치 저장 완료: {_gps_school} ({_gps_lat:.6f}, {_gps_lng:.6f})"
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

        # ── GPS 좌표 맵 구성 (음성 근접 매칭용) ─────────
        _cust_gps_map = {}
        for _s in schools:
            _ci = _cust_info_map.get(_s, {})
            _cust_full = {}
            # customer_info에서 좌표 가져오기
            for _cr in (_cust_rows if isinstance(_cust_rows, list) else []):
                if _cr.get('name') == _s:
                    _cust_full = _cr
                    break
            _cust_gps_map[_s] = {
                'cust_type': _ci.get('cust_type', '학교'),
                'lat': float(_cust_full.get('latitude', 0) or 0),
                'lng': float(_cust_full.get('longitude', 0) or 0),
            }

        # ── 음성 입력 (전체 거래처 대상 · 자동 매칭 + GPS) ─────────
        with st.expander("🎤 음성으로 수거량 입력 (자동 등록)", expanded=False):
            st.caption('예: "안산고 음식물 200" · "학교" · "마트" → GPS 자동 매칭')
            _render_voice_input(schools, "drv", cust_gps_map=_cust_gps_map)

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

                # 📍 현재 위치 저장 버튼 (GPS 좌표 미등록 거래처만 표시)
                _gps_info = _cust_gps_map.get(school, {})
                _has_gps = (_gps_info.get('lat', 0) != 0 and _gps_info.get('lng', 0) != 0)
                if _has_gps:
                    st.caption(f"📍 위치 등록됨")
                else:
                    _gps_save_html = f"""
                    <button onclick="
                      if (navigator.geolocation) {{
                        var btn = this;
                        btn.textContent = '📍 위치 확인 중...';
                        btn.disabled = true;
                        navigator.geolocation.getCurrentPosition(
                          function(pos) {{
                            try {{
                              var doc = window.parent.document;
                              var inp = doc.querySelector('input[aria-label=\\'_gps_data_\\']');
                              if (inp) {{
                                inp.focus();
                                var nativeSetter = Object.getOwnPropertyDescriptor(
                                  window.HTMLInputElement.prototype, 'value'
                                ).set;
                                var data = JSON.stringify({{
                                  school: '{school}',
                                  lat: pos.coords.latitude,
                                  lng: pos.coords.longitude
                                }});
                                nativeSetter.call(inp, data);
                                var rk = Object.keys(inp).find(function(k) {{ return k.startsWith('__reactProps$'); }});
                                if (rk && inp[rk] && inp[rk].onChange) {{ inp[rk].onChange({{ target: inp }}); }}
                                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                setTimeout(function() {{
                                  inp.dispatchEvent(new KeyboardEvent('keydown', {{ key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true }}));
                                }}, 50);
                                setTimeout(function() {{
                                  inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                  inp.blur();
                                }}, 200);
                                btn.textContent = '📍 저장 완료!';
                              }} else {{
                                alert('브릿지를 찾을 수 없습니다. 페이지를 새로고침 해주세요.');
                              }}
                            }} catch(ex) {{
                              alert('위치 저장 오류: ' + ex.message);
                            }}
                          }},
                          function(err) {{ alert('위치 획득 실패: 위치 권한을 확인해 주세요'); btn.disabled = false; btn.textContent = '📍 현재 위치 저장 (첫 방문 시 1회)'; }},
                          {{ enableHighAccuracy: true, timeout: 5000 }}
                        );
                      }} else {{ alert('이 브라우저는 GPS를 지원하지 않습니다'); }}
                    " style="width:100%;padding:8px;font-size:13px;font-weight:700;
                       border:1px dashed #1a73e8;border-radius:8px;background:#f0f7ff;
                       color:#1a73e8;cursor:pointer;margin-bottom:4px;">
                      📍 현재 위치 저장 (첫 방문 시 1회)
                    </button>
                    """
                    components.html(_gps_save_html, height=44)

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

                    # 날짜 추가 버튼 (밀린 수거 입력용 — 여러 날짜 자유 추가)
                    if st.button("＋ 날짜 추가", key=f"drv_dr_add_{school}"):
                        _existing_dates = [r["date"] for r in st.session_state[_dr_key]]
                        # 기존 행에 없는 가장 최근 과거 날짜를 자동 계산
                        _new_date = today - timedelta(days=1)
                        for _d in range(1, 31):  # 최대 30일 전까지
                            _candidate = today - timedelta(days=_d)
                            if _candidate not in _existing_dates:
                                _new_date = _candidate
                                break
                        st.session_state[_dr_key].append(
                            {"date": _new_date, "weight": 0.0, "item": "음식물"}
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

        # 오늘 입력 현황 (created_at 기준 — 과거 날짜 입력분도 포함)
        st.divider()
        st.markdown("#### 📋 오늘 입력 현황")
        today_input_all = [r for r in db_get('real_collection')
                           if r.get('driver') == driver_name
                           and str(r.get('created_at', ''))[:10] == today_str]
        if not today_input_all:
            st.info("오늘 입력된 수거 실적이 없습니다.")
        else:
            df = pd.DataFrame(today_input_all)
            if 'status' in df.columns:
                df['status'] = df['status'].map({
                    'draft':     '📋 임시저장',
                    'submitted': '✅ 전송완료',
                }).fillna(df['status'])
            show = [c for c in ['collect_date','school_name','item_type','weight','status','memo']
                    if c in df.columns]
            if 'collect_date' in df.columns:
                df = df.rename(columns={'collect_date': '수거일자'})
                show = ['수거일자' if c == 'collect_date' else c for c in show]
            st.dataframe(df[show], use_container_width=True, hide_index=True)
            m1, m2 = st.columns(2)
            with m1:
                st.metric("오늘 입력 수거량", f"{df['weight'].sum():,.1f} kg")
            with m2:
                submitted = len([r for r in today_input_all if r.get('status') == 'submitted'])
                st.metric("전송 완료", f"{submitted}건")

    st.divider()

    # ══════════════════════════════════════════════
    # 섹션3: 처리확인 (계근표)
    # ══════════════════════════════════════════════
    st.markdown("### ⚖️ 처리확인 (계근표)")
    st.caption("처리장 도착 후 계근표 사진 촬영 및 처리량을 입력하세요.")

    # GPS 위치 자동 취득 (JavaScript)
    _proc_gps_key = f"_proc_gps_{driver_name}"
    _proc_gps_bridge = f"_proc_gps_bridge_{driver_name}"

    st.components.v1.html(f"""
    <script>
    (function() {{
        if (navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(
                function(pos) {{
                    var lat = pos.coords.latitude;
                    var lng = pos.coords.longitude;
                    var data = JSON.stringify({{lat: lat, lng: lng}});
                    // Streamlit hidden text bridge
                    var el = window.parent.document.querySelector(
                        'input[aria-label="proc_gps_hidden"]');
                    if (el) {{
                        var nativeSet = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value').set;
                        nativeSet.call(el, data);
                        el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    }}
                }},
                function(err) {{ console.log('GPS error:', err.message); }},
                {{enableHighAccuracy: true, timeout: 10000}}
            );
        }}
    }})();
    </script>
    """, height=0)

    # ── GPS 브릿지 입력 (완전 숨김 처리) ──
    st.markdown("""<style>
    div[data-testid="stTextInput"]:has(input[aria-label="proc_gps_hidden"]) {
        position: absolute !important;
        width: 0 !important; height: 0 !important;
        overflow: hidden !important; opacity: 0 !important;
        pointer-events: none !important;
    }
    </style>""", unsafe_allow_html=True)

    gps_raw = st.text_input("proc_gps_hidden", value="", key=_proc_gps_bridge,
                            label_visibility="collapsed")
    proc_lat = 0.0
    proc_lng = 0.0
    if gps_raw:
        try:
            gps_data = json.loads(gps_raw)
            proc_lat = float(gps_data.get('lat', 0))
            proc_lng = float(gps_data.get('lng', 0))
        except (json.JSONDecodeError, ValueError):
            pass

    # GPS 상태 표시
    if proc_lat != 0 and proc_lng != 0:
        st.success(f"📍 GPS 위치 확인: {proc_lat:.6f}, {proc_lng:.6f}")

    # ── 계근표 입력 (접기/펼치기) ──
    with st.expander("📝 처리량 입력", expanded=True):
        pc1, pc2 = st.columns(2)
        with pc1:
            proc_weight = st.number_input("계근표 처리량 (kg)", min_value=0.0,
                                          step=10.0, format="%.1f",
                                          key="proc_weight")
        with pc2:
            proc_location = st.text_input("처리장명", key="proc_location",
                                          placeholder="예: ○○자원순환센터")

        # 계근표 사진 촬영
        with st.expander("📸 계근표 사진 (선택)", expanded=False):
            proc_photo = st.file_uploader(
                "사진 촬영 또는 갤러리에서 선택",
                type=['jpg', 'jpeg', 'png'],
                key="proc_photo",
                help="모바일: 촬영 또는 갤러리 선택 가능"
            )
            if proc_photo:
                st.image(proc_photo, caption="첨부된 계근표 사진", use_container_width=True)
                st.success("📸 사진이 첨부되었습니다.")

        proc_memo = st.text_input("메모 (선택)", key="proc_memo", placeholder="특이사항")

    if st.button("📤 처리확인 전송", type="primary", key="btn_proc_submit",
                 use_container_width=True):
        if proc_weight <= 0:
            st.error("처리량을 입력하세요.")
        elif not proc_location:
            st.error("처리장명을 입력하세요.")
        else:
            _proc_now = datetime.now(ZoneInfo('Asia/Seoul'))
            proc_data = {
                'vendor':         vendor,
                'driver':         driver_name,
                'confirm_date':   _proc_now.strftime('%Y-%m-%d'),
                'confirm_time':   _proc_now.strftime('%H:%M:%S'),
                'total_weight':   proc_weight,
                'photo_attached': 1 if proc_photo else 0,
                'latitude':       proc_lat,
                'longitude':      proc_lng,
                'location_name':  proc_location,
                'memo':           proc_memo,
                'status':         'submitted',
                'created_at':     _proc_now.strftime('%Y-%m-%d %H:%M:%S'),
            }
            ok = db_insert('processing_confirm', proc_data)
            if ok:
                st.success(f"✅ 처리확인 전송 완료! ({proc_weight:.1f}kg @ {proc_location})")
                st.balloons()
            else:
                st.error("전송 실패. 다시 시도해주세요.")

    # 오늘 처리확인 이력
    proc_today = [r for r in db_get('processing_confirm')
                  if r.get('driver') == driver_name
                  and str(r.get('confirm_date', '')) == today_str]
    if proc_today:
        st.markdown("##### 오늘 처리확인 이력")
        for pr in proc_today:
            _pw = float(pr.get('total_weight', 0))
            _loc = pr.get('location_name', '')
            _tm = pr.get('confirm_time', '')[:5]
            _ph = "📷" if int(pr.get('photo_attached', 0)) else ""
            _st = "✅" if pr.get('status') == 'confirmed' else "📤"
            st.markdown(f"- {_st} **{_tm}** | {_loc} | {_pw:.1f}kg {_ph}")

    st.divider()

    # ══════════════════════════════════════════════
    # 섹션4: 퇴근
    # ══════════════════════════════════════════════
    st.markdown("### 🏠 퇴근")

    # 퇴근 요약: created_at 기준 (과거 날짜 입력분도 포함)
    today_done_all = [r for r in db_get('real_collection')
                      if r.get('driver') == driver_name
                      and str(r.get('created_at', ''))[:10] == today_str]
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
