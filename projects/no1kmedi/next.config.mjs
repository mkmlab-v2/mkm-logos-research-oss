/** @type {import('next').NextConfig} */
const nextConfig = {
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
    ];
  },
};

export default nextConfig;
