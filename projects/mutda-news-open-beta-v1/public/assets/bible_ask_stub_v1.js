(function () {
  var STUB = {
    mode: "local_stub",
    live_api: false,
    logos_keep: "https://logos.jema-ai.com",
    slots: {
      passage: "데모 본문 앵커만 표시합니다. 실제 구절 잠금은 Logos 연구면에서 이어가세요.",
      context: "문맥 슬롯은 로컬 셸용입니다. 역사·문학 문맥 엔진은 여기 라이브 연결되지 않습니다.",
      reading: "해석은 [NON_GATING] 참고용입니다. 단일 교리·완성 선언을 하지 않습니다.",
      alt: "다른 관점 슬롯은 학파·독법을 병기하는 자리입니다. 승자를 고르지 않습니다.",
      evidence: "근거 슬롯은 citation 자리입니다. 현재는 로컬 데모 문구만 채웁니다."
    }
  };
  function fill(q) {
    var qTrim = (q || "").trim();
    document.getElementById("slot-passage").textContent =
      qTrim ? ("질문 반영(데모): " + qTrim.slice(0, 120) + " · " + STUB.slots.passage) : STUB.slots.passage;
    document.getElementById("slot-context").textContent = STUB.slots.context;
    document.getElementById("slot-reading").textContent = STUB.slots.reading;
    document.getElementById("slot-alt").textContent = STUB.slots.alt;
    document.getElementById("slot-evidence").textContent = STUB.slots.evidence;
    document.getElementById("bible-slots").hidden = false;
    document.getElementById("bible-more-btn").hidden = false;
  }
  function onAsk() {
    var ta = document.getElementById("bible-q");
    fill(ta ? ta.value : "");
  }
  function onMore() {
    var ta = document.getElementById("bible-q");
    if (ta) {
      ta.value = (ta.value || "").trim() + (ta.value && ta.value.trim() ? " · " : "") + "이어서: 근거 구절을 더 좁혀 주세요";
      ta.focus();
    }
  }
  document.addEventListener("DOMContentLoaded", function () {
    var ask = document.getElementById("bible-ask-btn");
    var more = document.getElementById("bible-more-btn");
    if (ask) ask.addEventListener("click", onAsk);
    if (more) more.addEventListener("click", onMore);
  });
})();
