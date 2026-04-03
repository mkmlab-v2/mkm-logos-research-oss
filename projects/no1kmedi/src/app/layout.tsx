import type { Metadata } from "next";
import { siteCopy } from "@/content/siteCopy";
import "./globals.css";

export const metadata: Metadata = {
  title: siteCopy.seo.title,
  description: siteCopy.seo.description,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="" />
        <link
          href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
