import Link from "next/link";
import { siteCopy } from "@/content/siteCopy";

export const metadata = {
  title: "회사 소개 | JEMA AI",
  description: "주식회사 목소리네트워크 법적 고지 및 연락처.",
};

export default function CompanyPage() {
  const f = siteCopy.footer;
  const positioning = siteCopy.positioning_v1?.footer_strip_ko;

  return (
    <main style={{ maxWidth: "900px", margin: "0 auto", padding: "2rem 1.25rem 3rem", lineHeight: 1.7 }}>
      <h1>회사 소개</h1>
      <p>
        <strong>{f.company_line}</strong> · {f.brand_subline}
      </p>
      <ul>
        <li>대표: Ki-ryun Lee</li>
        <li>
          {f.biz_reg_label}: {f.biz_reg}
        </li>
        <li>
          {f.address_label}: {f.address}
        </li>
        <li>
          문의: <a href={`mailto:${f.email}`}>{f.email}</a>
        </li>
      </ul>
      {positioning ? (
        <p role="note" style={{ marginTop: "1.5rem", fontSize: "0.95rem", color: "#555" }}>
          {positioning}
        </p>
      ) : null}
      <section
        aria-labelledby="company-disclaimer-title"
        style={{ marginTop: "1.75rem", paddingTop: "1.25rem", borderTop: "1px solid #ddd" }}
      >
        <h2 id="company-disclaimer-title" style={{ fontSize: "1.05rem", margin: "0 0 0.75rem" }}>
          안내
        </h2>
        <ul style={{ margin: 0, paddingLeft: "1.2rem", fontSize: "0.95rem", color: "#555" }}>
          <li>본 페이지는 법인·연락 안내입니다. 의료 진단·처방, 투자 권유, 실매매 지시가 아닙니다.</li>
          <li>제품·서비스는 각 도메인 입구에서 이어지며, 허브에서 하나로 합치지 않습니다.</li>
          <li>
            레인·하지 않는 일: <Link href="/safety">안전·고지</Link>
          </li>
        </ul>
      </section>
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/">브랜드 허브</Link>
        {" · "}
        <Link href="/hub">질문 안내</Link>
        {" · "}
        <Link href="/privacy">개인정보처리방침</Link>
        {" · "}
        <Link href="/terms">이용약관</Link>
      </p>
      <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "#666" }}>{f.rights}</p>
    </main>
  );
}
