import Link from "next/link";
import { siteCopy } from "@/content/siteCopy";

export const metadata = {
  title: "개인정보처리방침 | JEMA AI",
  description: "JEMA AI 서비스 개인정보 처리 방침.",
};

export default function PrivacyPage() {
  const f = siteCopy.footer;
  const positioning = siteCopy.positioning_v1?.footer_strip_ko;

  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1.25rem 3rem", lineHeight: 1.7 }}>
      <h1>개인정보처리방침</h1>
      <p>
        {f.company_line}(이하 &quot;회사&quot;)는 서비스 운영·고객 지원·법적 의무 이행에 필요한 범위에서만 개인정보를
        처리합니다.
      </p>
      <h2>수집·이용</h2>
      <ul>
        <li>수집 항목: 서비스 운영·문의 응대에 필요한 최소 정보</li>
        <li>보유 기간: 관련 법령 및 내부 정책에 따른 기간</li>
        <li>파기: 보유 기간 만료 시 안전하게 삭제</li>
      </ul>
      <h2>문의</h2>
      <p>
        개인정보 관련 문의: <a href={`mailto:${f.email}`}>{f.email}</a>
      </p>
      {positioning ? (
        <p role="note" style={{ marginTop: "1.5rem", fontSize: "0.95rem", color: "#555" }}>
          {positioning}
        </p>
      ) : null}
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/company">회사 소개</Link>
        {" · "}
        <Link href="/terms">이용약관</Link>
        {" · "}
        <Link href="/hub">허브로</Link>
      </p>
    </main>
  );
}
