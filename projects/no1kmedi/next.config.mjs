/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.MKM_NEXT_DIST_DIR || ".next",
  reactStrictMode: true,
  // Middleware (Edge) does not read .env.local unless inlined here.
  env: {
    MKM_DEV_SIMULATE_NO1KMEDI_HOST: process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST ?? "",
  },
  async headers() {
    return [
      {
        source: "/personadiary/sw.js",
        headers: [
          { key: "Service-Worker-Allowed", value: "/" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
        ],
      },
      {
        source: "/personadiary/manifest.webmanifest",
        headers: [{ key: "Cache-Control", value: "public, max-age=3600" }],
      },
      {
        source: "/personadiary",
        headers: [{ key: "Cache-Control", value: "no-store, must-revalidate" }],
      },
      {
        source: "/personadiary/:path*",
        headers: [{ key: "Cache-Control", value: "no-store, must-revalidate" }],
      },
      {
        source: "/auth.md",
        headers: [
          { key: "Content-Type", value: "text/markdown; charset=utf-8" },
          { key: "Cache-Control", value: "public, max-age=300" },
        ],
      },
    ];
  },
};

export default nextConfig;
