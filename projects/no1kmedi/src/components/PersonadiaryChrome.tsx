"use client";

import Link from "next/link";
import { personadiaryCopy } from "@/content/personadiaryCopy";

export function PersonadiaryChrome({
  children,
  premium = false,
}: {
  children: React.ReactNode;
  premium?: boolean;
}) {
  return (
    <div className={premium ? "pd-shell pd-shell--premium" : "pd-shell"}>
      <a className="skip" href="#main">
        본문으로 건너뛰기
      </a>
      <header className="pd-header">
        <div className="pd-header-inner">
          <Link className="pd-brand" href="/">
            {personadiaryCopy.brand.name}
            <span className="pd-tag">{personadiaryCopy.brand.tag}</span>
          </Link>
          <nav className="pd-nav" aria-label="Persona Diary">
            <Link href="/demo">콘셉트 데모</Link>
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
        </div>
      </header>
      {children}
      <footer className="pd-footer">
        <p>
          {personadiaryCopy.brand.name} · 콘셉트 프리뷰 · 의료·투자·법률 조언을
          제공하지 않습니다.
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
      `}</style>
    </div>
  );
}
