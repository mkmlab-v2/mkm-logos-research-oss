import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // 📦 정적 빌드 (VPS 배포용)
  // 주석 해제하면 정적 파일로 빌드 (Nginx에서 직접 서빙)
  // 주석 처리하면 Next.js 서버 모드 (PM2로 실행)
  // output: 'export',

  /** dev에서 Playwright·다른 포트 클라이언트가 같은 호스트로 `_next`를 요청할 때 경고 완화 */
  allowedDevOrigins: [
    'localhost',
    '127.0.0.1',
    'http://127.0.0.1',
    'http://localhost',
    'http://127.0.0.1:3000',
    'http://localhost:3000',
    'http://127.0.0.1:3333',
    'http://localhost:3333',
  ],

  /** RSC/번들에서 외부 패키지 처리 — Next 15+: experimental.serverComponentsExternalPackages 대체 */
  serverExternalPackages: ['@google/generative-ai'],

  // 📊 성능 최적화
  compiler: {
    // 프로덕션 빌드 최적화
    removeConsole: process.env.NODE_ENV === 'production',
  },
  
  // 🖼️ 이미지 최적화
  images: {
    domains: ['localhost', 'vercel.app'],
    formats: ['image/webp', 'image/avif'],
  },
  
  // 🔒 보안 헤더
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
  
  // 🌐 환경 변수 최적화
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },
  
  // 📦 번들 최적화 + Tauri/Capacitor 클라이언트 번들 호환 (구 next.config.js)
  webpack: (config, { dev, isServer }) => {
    config.watchOptions = {
      ...config.watchOptions,
      ignored: ['**/android/**', '**/node_modules/**'],
    };

    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        '@tauri-apps/api/core': false,
        '@tauri-apps/api': false,
        child_process: false,
        fs: false,
        path: false,
      };

      config.externals = config.externals || [];
      config.externals.push({
        '@tauri-apps/api/core': 'commonjs @tauri-apps/api/core',
        '@tauri-apps/api': 'commonjs @tauri-apps/api',
        '@capacitor/keyboard': 'commonjs @capacitor/keyboard',
        '@capacitor/haptics': 'commonjs @capacitor/haptics',
      });
    }

    if (!dev && !isServer) {
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            chunks: 'all',
          },
        },
      };
    }
    return config;
  },
  
  // android 폴더 제외 (TypeScript 컴파일)
  typescript: {
    ignoreBuildErrors: false,
  },
  
  // android 폴더 제외 (ESLint)
  eslint: {
    ignoreDuringBuilds: false,
    dirs: ['app', 'src'],
  },
};

export default nextConfig;
