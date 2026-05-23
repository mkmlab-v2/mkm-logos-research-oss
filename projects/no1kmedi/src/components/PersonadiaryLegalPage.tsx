import Link from "next/link";
import type { ReactNode } from "react";
import { PersonadiaryChrome } from "@/components/PersonadiaryChrome";

export function PersonadiaryLegalPage({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <PersonadiaryChrome>
      <main id="main" className="pd-legal">
        <p className="pd-legal-back">
          <Link href="/">← 홈</Link>
        </p>
        <h1>{title}</h1>
        <div className="pd-legal-body">{children}</div>
      </main>
    </PersonadiaryChrome>
  );
}
