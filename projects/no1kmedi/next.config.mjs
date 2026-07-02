/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.MKM_NEXT_DIST_DIR || ".next",
  reactStrictMode: true,
  webpack: (config, { dev }) => {
    // Windows + monorepo: optional poll when WATCHPACK_POLLING or MKM_NEXT_DEV_POLL is set.
    if (
      dev &&
      (process.env.WATCHPACK_POLLING === "true" || process.env.MKM_NEXT_DEV_POLL === "1")
    ) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
        ignored: ["**/node_modules/**", "**/.git/**"],
      };
    }
    return config;
  },
  // Middleware (Edge) does not read .env.local unless inlined here.
  env: {
    MKM_DEV_SIMULATE_LOGOS_HOST: process.env.MKM_DEV_SIMULATE_LOGOS_HOST ?? "",
    NEXT_PUBLIC_MKM_DEV_SIMULATE_LOGOS_HOST:
      process.env.NEXT_PUBLIC_MKM_DEV_SIMULATE_LOGOS_HOST ??
      process.env.MKM_DEV_SIMULATE_LOGOS_HOST ??
      "",
    MKM_DEV_SIMULATE_NO1KMEDI_HOST: process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST ?? "",
  },
  async redirects() {
    return [
      {
        source: "/engine",
        destination: "/validation",
        permanent: true,
      },
      {
        source: "/lanes",
        destination: "/safety",
        permanent: true,
      },
    ];
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
