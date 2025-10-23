import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
      },
    ];
  },
  // Image optimization configuration
  // Configured with Next.js 16 defaults explicitly set for clarity
  images: {
    minimumCacheTTL: 14400, // 4 hours (Next.js 16 default, increased from 60s)
    qualities: [50, 75, 100], // Support multiple quality levels (75 is default)
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384], // Include 16px (removed in v16 default)
    maximumRedirects: 3, // Next.js 16 default (changed from unlimited)
  },
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
