import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const FARM_HOSTS = new Set(["farm.jema-ai.com", "www.farm.jema-ai.com"]);
const FARM_CANONICAL_ORIGIN = "https://farm.jema-ai.com";
/** Hub hosts: /smartfarm on apex/app is redirected to farm.jema-ai.com (B2B canonical). */
const JEMA_HUB_HOSTS = new Set([
  "jema-ai.com",
  "www.jema-ai.com",
  "app.jema-ai.com",
  "www.app.jema-ai.com",
]);
/** O-P5: www.jema12.com/studio → jema-ai.com/studio → app.jema-ai.com/studio (CF) → oracle v6 */
const STUDIO_ORACLE_V6_URL =
  "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1";
const PERSONADIARY_HOSTS = new Set([
  "personadiary.com",
  "www.personadiary.com",
  "preview.personadiary.com",
]);
/** 한의사 진료 보조 — clinic.no1kmedi.com (공식 브랜드 URL은 app.jema-ai.com/clinician). */
const CLINIC_NO1KMEDI_HOSTS = new Set([
  "clinic.no1kmedi.com",
  "www.clinic.no1kmedi.com",
]);
/** no1kmedi apex — 한의사 포털 진입(동일 Next, /clinician). api.* 는 별도 nginx vhost. */
const NO1KMEDI_APEX_PORTAL_HOSTS = new Set([
  "no1kmedi.com",
  "www.no1kmedi.com",
]);

function rewriteToClinicianPath(pathname: string): string {
  if (pathname === "/clinician" || pathname.startsWith("/clinician/")) {
    return pathname;
  }
  return pathname === "/" ? "/clinician" : `/clinician${pathname}`;
}

function shouldPassThroughStaticOrApi(pathname: string): boolean {
  return (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  );
}

function isStudioPath(pathname: string): boolean {
  return (
    pathname === "/studio" ||
    pathname === "/studio/" ||
    pathname.startsWith("/studio/")
  );
}

export function middleware(request: NextRequest) {
  const host = (request.headers.get("host") ?? "").split(":")[0]?.toLowerCase();
  const { pathname } = request.nextUrl;

  if (isStudioPath(pathname)) {
    return NextResponse.redirect(STUDIO_ORACLE_V6_URL, 301);
  }

  if (
    JEMA_HUB_HOSTS.has(host) &&
    (pathname === "/smartfarm" || pathname.startsWith("/smartfarm/"))
  ) {
    const suffix =
      pathname === "/smartfarm" || pathname === "/smartfarm/"
        ? "/"
        : pathname.replace(/^\/smartfarm/, "");
    return NextResponse.redirect(`${FARM_CANONICAL_ORIGIN}${suffix}`, 308);
  }

  if (!host) {
    return NextResponse.next();
  }

  if (CLINIC_NO1KMEDI_HOSTS.has(host) || NO1KMEDI_APEX_PORTAL_HOSTS.has(host)) {
    if (shouldPassThroughStaticOrApi(pathname)) {
      return NextResponse.next();
    }
    const url = request.nextUrl.clone();
    url.pathname = rewriteToClinicianPath(pathname);
    return NextResponse.rewrite(url);
  }

  if (PERSONADIARY_HOSTS.has(host)) {
    if (pathname === "/demo" || pathname === "/demo/") {
      const url = request.nextUrl.clone();
      url.pathname = "/personadiary-concept-demo.html";
      return NextResponse.rewrite(url);
    }
    if (shouldPassThroughStaticOrApi(pathname)) {
      return NextResponse.next();
    }
    if (pathname === "/personadiary" || pathname.startsWith("/personadiary/")) {
      return NextResponse.next();
    }
    const url = request.nextUrl.clone();
    url.pathname = pathname === "/" ? "/personadiary" : `/personadiary${pathname}`;
    return NextResponse.rewrite(url);
  }

  if (!FARM_HOSTS.has(host)) {
    return NextResponse.next();
  }

  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  if (pathname === "/smartfarm" || pathname.startsWith("/smartfarm/")) {
    return NextResponse.next();
  }

  const url = request.nextUrl.clone();
  url.pathname = pathname === "/" ? "/smartfarm" : `/smartfarm${pathname}`;
  return NextResponse.rewrite(url);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
