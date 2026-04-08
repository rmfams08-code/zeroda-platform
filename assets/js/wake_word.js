/* ============================================================
 * zeroda 기사모드 웨이크워드 — 클라이언트 JS
 * ------------------------------------------------------------
 * 저장 위치 : assets/js/wake_word.js
 * 로드 위치 : driver.py 의 rx.script(src="/static/js/wake_word.js")
 *
 * 동작 흐름
 *   1) startWakeWord()  → 백그라운드 연속 STT 루프 시작
 *   2) 발화 중 "수거"/"입력"/"제로다" 키워드 감지 시
 *      → window.dispatchEvent(new CustomEvent('zeroda-wake'))
 *   3) "완료"/"끝" 감지 시 stopWakeWord() 호출
 *   4) Wake Lock으로 화면 꺼짐 방지 (배터리 모드라도 OK)
 *   5) 블루투스 마이크 자동 우선 선택
 *
 * ⚠️ 사례5 준수: Reflex Var 와 직접 결합하지 않음 (순수 JS)
 *               state로 결과 전달은 CustomEvent + rx.call_script 방식
 * ============================================================ */

(function () {
  if (window.__zerodaWake) return;     // 이중 초기화 방지
  window.__zerodaWake = {
    recognition: null,
    running:     false,
    wakeLock:    null,
    keywords: {
      start:  ["수거", "입력", "기록", "제로다"],
      stop:   ["완료", "끝", "종료", "오프"],
      cancel: ["취소"],
    },
    lastFireAt: 0,    // 중복 트리거 방지 (1.5초 쿨다운)
  };

  const W = window.__zerodaWake;

  // ── 1) Wake Lock (화면 꺼짐 방지) ──
  async function acquireWakeLock() {
    try {
      if ("wakeLock" in navigator) {
        W.wakeLock = await navigator.wakeLock.request("screen");
        W.wakeLock.addEventListener("release", () => { W.wakeLock = null; });
      }
    } catch (e) { console.warn("[wake] wakeLock 실패:", e); }
  }
  function releaseWakeLock() {
    if (W.wakeLock) { try { W.wakeLock.release(); } catch (e) {} W.wakeLock = null; }
  }

  // ── 2) 블루투스 마이크 우선 선택 ──
  async function pickBluetoothMic() {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const bt = devices.find(d =>
        d.kind === "audioinput" &&
        /bluetooth|airpod|buds|headset|이어/i.test(d.label)
      );
      return bt ? bt.deviceId : null;
    } catch (e) { return null; }
  }

  // ── 3) 키워드 매칭 ──
  function matchKeyword(text, list) {
    const t = (text || "").replace(/\s+/g, "");
    return list.some(k => t.includes(k));
  }

  // ── 4) 메인 루프 ──
  async function loop() {
    if (!W.running) return;

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      console.warn("[wake] 이 브라우저는 SpeechRecognition 미지원");
      W.running = false;
      return;
    }

    const r = new SR();
    r.lang = "ko-KR";
    r.continuous = false;
    r.interimResults = false;
    r.maxAlternatives = 1;

    r.onresult = (e) => {
      const txt = (e.results[0] && e.results[0][0].transcript) || "";
      console.log("[wake] heard:", txt);

      const now = Date.now();
      if (now - W.lastFireAt < 1500) return;   // 쿨다운

      if (matchKeyword(txt, W.keywords.stop)) {
        W.lastFireAt = now;
        stopWakeWord();
        showToast("🎤 음성 입력 종료");
        return;
      }
      if (matchKeyword(txt, W.keywords.cancel)) {
        W.lastFireAt = now;
        window.dispatchEvent(new CustomEvent("zeroda-wake-cancel"));
        return;
      }
      if (matchKeyword(txt, W.keywords.start)) {
        W.lastFireAt = now;
        showToast("🎤 호출 감지 — 입력 대기");
        window.dispatchEvent(new CustomEvent("zeroda-wake"));
        return;
      }
    };

    r.onerror = (e) => {
      // not-allowed: 권한 거부 → 루프 중지, 그 외는 재시작
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        console.warn("[wake] 권한 거부");
        W.running = false;
        return;
      }
    };

    r.onend = () => {
      if (W.running) setTimeout(loop, 200);    // 자동 재시작
    };

    try { r.start(); W.recognition = r; }
    catch (e) {
      console.warn("[wake] start 실패:", e);
      if (W.running) setTimeout(loop, 800);
    }
  }

  // ── 5) Public API ──
  async function startWakeWord() {
    if (W.running) return;
    W.running = true;
    await acquireWakeLock();

    // 마이크 권한 사전 요청 (블루투스 선택은 best-effort)
    try {
      const bt = await pickBluetoothMic();
      const constraints = bt
        ? { audio: { deviceId: { exact: bt } } }
        : { audio: true };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      stream.getTracks().forEach(t => t.stop());   // 권한만 확보 후 즉시 해제
    } catch (e) { console.warn("[wake] 마이크 권한 실패:", e); }

    showToast("🎧 웨이크워드 ON — '수거' 라고 말하세요");
    loop();
  }

  function stopWakeWord() {
    W.running = false;
    if (W.recognition) {
      try { W.recognition.stop(); } catch (e) {}
      W.recognition = null;
    }
    releaseWakeLock();
  }

  function showToast(msg) {
    const el = document.getElementById("wake-toast");
    if (el) {
      el.textContent = msg;
      el.style.display = "block";
      clearTimeout(el.__t);
      el.__t = setTimeout(() => { el.style.display = "none"; }, 2500);
    }
  }

  // 글로벌 노출
  window.zerodaWake = { start: startWakeWord, stop: stopWakeWord };

  // 페이지 전환/숨김 시 자동 정지 (배터리 보호)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden" && W.running) stopWakeWord();
  });
})();
