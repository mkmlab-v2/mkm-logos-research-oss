import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const FARM_HOSTS = new Set(["farm.jema-ai.com", "www.farm.jema-ai.com"]);
/** O-P5: www.jema12.com/studio → jema-ai.com/studio → app.jema-ai.com/studio (CF) → oracle v6 */
const STUDIO_ORACLE_V6_URL =
  "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1";
const PERSONADIARY_HOSTS = new Set([
  "personadiary.com",
  "www.personadiary.com",
  "preview.personadiary.com",
]);

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

  if (!host) {
    return NextResponse.next();
  }

  if (PERSONADIARY_HOSTS.has(host)) {
    if (pathname === "/demo" || pathname === "/demo/") {
      const url = request.nextUrl.clone();
      url.pathname = "/personadiary-concept-demo.html";
      return NextResponse.rewrite(url);
    }
    if (
      pathname.startsWith("/_next") ||
      pathname.startsWith("/api") ||
      pathname.includes(".")
    ) {
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
