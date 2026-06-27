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
      <p style={{ marginTop: "1.5rem" }}>
        <Link href="/hub">허브로</Link>
        {" · "}
        <Link href="/privacy">개인정보처리방침</Link>
        {" · "}
        <Link href="/terms">이용약관</Link>
      </p>
      <p style={{ marginTop: "1rem", fontSize: "0.85rem", color: "#666" }}>{f.rights}</p>
    </main>
  );
}
