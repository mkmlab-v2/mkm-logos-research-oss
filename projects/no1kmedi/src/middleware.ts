import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  isPublicPatientSurfacePath,
  normalizeRequestHost,
  shouldRewriteRootToClinician,
} from "@/lib/no1kmedi-portal-host";

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
  const host = normalizeRequestHost(request.headers.get("host"));
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

  if (shouldRewriteRootToClinician(host)) {
    if (shouldPassThroughStaticOrApi(pathname)) {
      return NextResponse.next();
    }
    if (isPublicPatientSurfacePath(pathname)) {
      return NextResponse.next();
    }
    const targetPath = rewriteToClinicianPath(pathname);
    if (targetPath === pathname) {
      return NextResponse.next();
    }
    const url = request.nextUrl.clone();
    url.pathname = targetPath;
    // Redirect (not rewrite) so the browser URL shows /clinician — avoids stale hub cache on /.
    return NextResponse.redirect(url);
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
