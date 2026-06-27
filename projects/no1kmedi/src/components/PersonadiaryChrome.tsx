"use client";

import Link from "next/link";
import { personadiaryCopy } from "@/content/personadiaryCopy";
import { personadiaryPublicPath } from "@/lib/personadiaryMobileOpsV1";
import { PersonadiaryHubFooter } from "@/components/personadiary/PersonadiaryHubFooter";

export function PersonadiaryChrome({
  children,
  premium = false,
  ops = false,
}: {
  children: React.ReactNode;
  premium?: boolean;
  /** PWA /ops — minimal chrome (no marketing nav · slim footer) */
  ops?: boolean;
}) {
  const shellClass = [
    "pd-shell",
    premium || ops ? "pd-shell--premium" : "",
    ops ? "pd-shell--ops" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={shellClass}>
      <a className="skip" href="#main">
        본문으로 건너뛰기
      </a>
      <header className={ops ? "pd-header pd-header--ops" : "pd-header"}>
        <div className="pd-header-inner">
          {ops ? (
            <>
              <Link className="pd-brand pd-brand--ops" href={personadiaryPublicPath("/ops")}>
                Persona Diary
              </Link>
              <nav className="pd-nav pd-nav--ops" aria-label="기지">
                <Link href={personadiaryPublicPath("")}>홈</Link>
              </nav>
            </>
          ) : (
            <>
              <Link className="pd-brand" href="/">
                {personadiaryCopy.brand.name}
                <span className="pd-tag">{personadiaryCopy.brand.tag}</span>
              </Link>
              <nav className="pd-nav" aria-label="Persona Diary">
                <Link href={personadiaryPublicPath("/ops")}>내 기지</Link>
                <Link href={personadiaryCopy.links.demo}>콘셉트 데모</Link>
                <a
                  href={personadiaryCopy.links.observatory}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  관측소 (v6)
                </a>
                <Link href={personadiaryCopy.links.waitlist}>사전 알림</Link>
                <a href={personadiaryCopy.links.contact}>문의</a>
              </nav>
            </>
          )}
        </div>
      </header>
      {children}
      <footer className={ops ? "pd-footer pd-footer--ops" : "pd-footer"}>
        {!ops && <PersonadiaryHubFooter />}
        <p>
          {ops
            ? "preview_only · 로컬 저장 · 의료·투자 조언 아님"
            : `${personadiaryCopy.brand.name} · 콘셉트 프리뷰 · 의료·투자·법률 조언을 제공하지 않습니다.`}
        </p>
        <p className="pd-footer-links">
          <Link href={personadiaryCopy.links.privacy}>개인정보</Link>
          <span aria-hidden="true"> · </span>
          <Link href={personadiaryCopy.links.terms}>이용약관</Link>
        </p>
      </footer>
      <style jsx global>{`
        .pd-shell {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }
        .pd-shell--premium {
          background: #030712;
          color: #e2e8f0;
        }
        .pd-shell--ops.pd-shell--premium {
          background: #000000;
        }
        .pd-shell--premium .pd-header {
          background: rgba(3, 7, 18, 0.88);
          border-bottom-color: rgba(255, 255, 255, 0.06);
        }
        .pd-header {
          border-bottom: 1px solid rgba(255, 255, 255, 0.08);
          background: rgba(2, 6, 23, 0.92);
          backdrop-filter: blur(12px);
          position: sticky;
          top: 0;
          z-index: 40;
        }
        .pd-header-inner {
          max-width: 960px;
          margin: 0 auto;
          padding: 0.85rem 1.25rem;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 1rem;
          flex-wrap: wrap;
        }
        .pd-brand {
          font-weight: 700;
          letter-spacing: 0.02em;
          color: inherit;
          text-decoration: none;
        }
        .pd-tag {
          margin-left: 0.5rem;
          font-size: 0.65rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          padding: 0.15rem 0.45rem;
          border-radius: 999px;
          border: 1px solid rgba(52, 211, 153, 0.35);
          color: #6ee7b7;
          vertical-align: middle;
        }
        .pd-nav {
          display: flex;
          gap: 1rem;
          font-size: 0.85rem;
        }
        .pd-nav a {
          color: rgba(226, 232, 240, 0.75);
          text-decoration: none;
        }
        .pd-nav a:hover {
          color: #fff;
        }
        .pd-footer {
          margin-top: auto;
          padding: 1.5rem 1.25rem 2rem;
          text-align: center;
          font-size: 0.72rem;
          color: rgba(148, 163, 184, 0.85);
          border-top: 1px solid rgba(255, 255, 255, 0.06);
        }
        .pd-footer-links {
          margin-top: 0.65rem;
        }
        .pd-footer-links a {
          color: rgba(148, 163, 184, 0.95);
          text-decoration: none;
        }
        .pd-footer-links a:hover {
          color: #6ee7b7;
        }
        .pd-hub-footer {
          margin-bottom: 1.25rem;
          padding-bottom: 1.25rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        .pd-hub-footer-kicker {
          margin: 0 0 0.65rem;
          font-size: 0.68rem;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: rgba(148, 163, 184, 0.75);
        }
        .pd-hub-footer-links {
          justify-content: center;
          margin-bottom: 0.5rem;
        }
        .pd-hub-footer-links .hub-pill-link,
        .pd-hub-pill-link {
          display: inline-flex;
          align-items: center;
          font-size: 0.78rem;
          font-weight: 500;
          color: rgba(226, 232, 240, 0.9);
          text-decoration: none;
          border: 1px solid rgba(52, 211, 153, 0.28);
          border-radius: 999px;
          padding: 0.35rem 0.75rem;
          background: rgba(6, 78, 59, 0.18);
          transition: border-color 0.15s ease, color 0.15s ease;
        }
        .pd-hub-footer-links .hub-pill-link:hover,
        .pd-hub-pill-link:hover {
          border-color: rgba(110, 231, 183, 0.55);
          color: #6ee7b7;
        }
        .pd-hub-pill-link--brand {
          margin-top: 0.35rem;
        }
        .pd-hub-footer-note {
          margin: 0.75rem auto 0;
          max-width: 36rem;
          font-size: 0.68rem;
          line-height: 1.45;
          color: rgba(148, 163, 184, 0.7);
        }
      `}</style>
    </div>
  );
}
