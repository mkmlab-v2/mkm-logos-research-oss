/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Middleware (Edge) does not read .env.local unless inlined here.
  env: {
    MKM_DEV_SIMULATE_NO1KMEDI_HOST: process.env.MKM_DEV_SIMULATE_NO1KMEDI_HOST ?? "",
  },
};

export default nextConfig;
