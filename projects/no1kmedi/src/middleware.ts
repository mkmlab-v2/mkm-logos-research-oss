import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  LOCAL_DEV_HOSTS,
  devSimulateLogosHost,
  isNationalKmAskPath,
  isPublicPatientSurfacePath,
  JEMA_AI_HUB_HOSTS,
  normalizeRequestHost,
  shouldRedirectRootToHubHome,
  shouldRewriteRootToClinician,
  shouldRewriteRootToNationalKmAsk,
} from "@/lib/no1kmedi-portal-host";
import { JEMAAI_CLOUD_PUBLIC_OBSERVE_URL } from "@/lib/jemaaiShowroomPublicV1";

const FARM_HOSTS = new Set(["farm.jema-ai.com", "www.farm.jema-ai.com"]);
const FARM_CANONICAL_ORIGIN = "https://farm.jema-ai.com";
const LOGOS_HOSTS = new Set(["logos.jema-ai.com", "www.logos.jema-ai.com"]);
const LOGOS_CANONICAL_ORIGIN = "https://logos.jema-ai.com";
/** Hub hosts: /smartfarm on apex/app is redirected to farm.jema-ai.com (B2B canonical). */
/** O-P5: /studio on hub hosts → public text-only observe surface on jemaai.cloud */
const STUDIO_ORACLE_V6_URL = JEMAAI_CLOUD_PUBLIC_OBSERVE_URL;
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

function isHubOperatorPath(pathname: string): boolean {
  return pathname === "/hub/operator" || pathname.startsWith("/hub/operator/");
}

/** Contract: operator_wtt auth internal_only — public URL must 403 unless dogfood build flag. */
function hubOperatorAccessDenied(): NextResponse {
  return new NextResponse("Forbidden — operator panel is internal-only.", {
    status: 403,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}

export function middleware(request: NextRequest) {
  const host = normalizeRequestHost(request.headers.get("host"));
  const { pathname } = request.nextUrl;
  const logosDevHost = LOCAL_DEV_HOSTS.has(host) && devSimulateLogosHost();

  if (isHubOperatorPath(pathname)) {
    if (process.env.NEXT_PUBLIC_UNIVERSE_HUB_OPERATOR_PANEL !== "1") {
      return hubOperatorAccessDenied();
    }
  }

  if (isStudioPath(pathname)) {
    return NextResponse.redirect(STUDIO_ORACLE_V6_URL, 301);
  }

  if (
    JEMA_AI_HUB_HOSTS.has(host) &&
    (pathname === "/smartfarm" || pathname.startsWith("/smartfarm/"))
  ) {
    const suffix =
      pathname === "/smartfarm" || pathname === "/smartfarm/"
        ? "/"
        : pathname.replace(/^\/smartfarm/, "");
    return NextResponse.redirect(`${FARM_CANONICAL_ORIGIN}${suffix}`, 308);
  }

  if (
    JEMA_AI_HUB_HOSTS.has(host) &&
    (pathname === "/logos-research" || pathname.startsWith("/logos-research/"))
  ) {
    const suffix =
      pathname === "/logos-research" || pathname === "/logos-research/"
        ? "/"
        : pathname.replace(/^\/logos-research/, "");
    return NextResponse.redirect(`${LOGOS_CANONICAL_ORIGIN}${suffix}`, 308);
  }

  if (!host) {
    return NextResponse.next();
  }

  if (shouldRedirectRootToHubHome(host, pathname, request.nextUrl.searchParams.get("legacy_home"))) {
    const url = request.nextUrl.clone();
    url.pathname = "/hub";
    url.search = "";
    return NextResponse.redirect(url);
  }

  if (shouldRewriteRootToNationalKmAsk(host)) {
    if (shouldPassThroughStaticOrApi(pathname)) {
      return NextResponse.next();
    }
    if (isNationalKmAskPath(pathname)) {
      return NextResponse.next();
    }
    if (isPublicPatientSurfacePath(pathname)) {
      return NextResponse.next();
    }
    if (pathname === "/clinician" || pathname.startsWith("/clinician/")) {
      return NextResponse.next();
    }
    if (pathname === "/") {
      const url = request.nextUrl.clone();
      url.pathname = "/ask";
      return NextResponse.redirect(url);
    }
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
    if (pathname === "/favicon.ico") {
      const url = request.nextUrl.clone();
      url.pathname = "/personadiary/icon-192.svg";
      return NextResponse.rewrite(url);
    }
    if (pathname === "/home" || pathname === "/home/") {
      return NextResponse.redirect(new URL("/", request.url), 308);
    }
    if (shouldPassThroughStaticOrApi(pathname)) {
      return NextResponse.next();
    }
    if (
      pathname === "/personadiary/manifest.webmanifest" ||
      pathname === "/personadiary/sw.js" ||
      pathname.startsWith("/personadiary/icon-")
    ) {
      return NextResponse.next();
    }
    if (pathname === "/personadiary" || pathname === "/personadiary/") {
      return NextResponse.redirect(new URL("/", request.url), 308);
    }
    if (pathname.startsWith("/personadiary/")) {
      const rest = pathname.slice("/personadiary".length) || "/";
      return NextResponse.redirect(new URL(rest, request.url), 308);
    }
    const url = request.nextUrl.clone();
    url.pathname = pathname === "/" ? "/personadiary" : `/personadiary${pathname}`;
    return NextResponse.rewrite(url);
  }

  if (!FARM_HOSTS.has(host) && !LOGOS_HOSTS.has(host) && !logosDevHost) {
    return NextResponse.next();
  }

  if (LOGOS_HOSTS.has(host) || logosDevHost) {
    if (
      pathname.startsWith("/_next") ||
      pathname.startsWith("/api") ||
      pathname.includes(".")
    ) {
      return NextResponse.next();
    }
    if (pathname === "/logos-research" || pathname.startsWith("/logos-research/")) {
      return NextResponse.next();
    }
    // Local Logos dev: redirect (not rewrite) so stale `/` HTML cache cannot show legacy HQ/clinician.
    if (logosDevHost && LOCAL_DEV_HOSTS.has(host) && pathname === "/") {
      return NextResponse.redirect(new URL("/logos-research", request.url), 307);
    }
    const url = request.nextUrl.clone();
    url.pathname = pathname === "/" ? "/logos-research" : `/logos-research${pathname}`;
    return NextResponse.rewrite(url);
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
  matcher: ["/((?!_next/static|_next/image).*)"],
};
