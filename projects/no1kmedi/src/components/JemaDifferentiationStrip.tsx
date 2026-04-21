"use client";

export function JemaDifferentiationStrip() {
  return (
    <aside className="jema-diff-strip" aria-label="JEMA AI 차별점">
      <p>
        <strong>JEMA AI 일반인 화면</strong>은 상담 전 참고 정보를 정리하는 보조 도구입니다. 본 대화는{" "}
        <strong>이 브라우저에만 임시 저장</strong>되며(로그인·서버 동기화 없음), 민감 정보 입력은 최소화해 주세요.
        요청 시 최근 대화와 사전문진 스냅샷이 함께 전송될 수 있습니다.
      </p>
      <p className="jema-diff-strip-sub">
        본 화면은 의료행위를 대체하지 않으며, <strong>최종 진단·처방 판단은 의료진이 직접 확정</strong>합니다.
        응급 증상이 의심되면 즉시 119 또는 응급실을 이용해 주세요.
      </p>
    </aside>
  );
}
