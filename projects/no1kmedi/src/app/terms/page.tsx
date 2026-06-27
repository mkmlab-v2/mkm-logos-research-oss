import Link from "next/link";
import { siteCopy } from "@/content/siteCopy";

export const metadata = {
  title: "이용약관 | JEMA AI",
  description: "JEMA AI 서비스 이용약관 및 면책.",
};

export default function TermsPage() {
  const f = siteCopy.footer;
  const positioning = siteCopy.positioning_v1?.footer_strip_ko;

  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1.25rem 3rem", lineHeight: 1.7 }}>
      <h1>이용약관</h1>
      <p>
        본 서비스는 웰니스·의사결정 보조를 위한 관측·리포트 인프라를 제공합니다. 진단·치료·처방을 대체하지 않으며,
        투자·법률 판단의 유일한 근거로 사용할 수 없습니다.
      </p>
      <p>
        최종 판단과 실행은 이용자 책임이며, 필요 시 자격을 갖춘 전문가와 상담해야 합니다. 서비스 내용·가용성은 법적·
        안전·운영상의 사유로 사전 통지 없이 변경될 수 있습니다.
      </p>
      {positioning ? (
        <p role="note" style={{ marginTop: "1.5rem", fontSize: "0.95rem", color: "#555" }}>
          {positioning}
        </p>
      ) : null}
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/company">회사 소개</Link>
        {" · "}
        <Link href="/privacy">개인정보처리방침</Link>
        {" · "}
        <Link href="/hub">허브로</Link>
      </p>
      <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "#666" }}>{f.rights}</p>
    </main>
  );
}
