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
  // Configured with Next.js 15 defaults explicitly set for clarity
  images: {
    minimumCacheTTL: 14400, // 4 hours cache time
    formats: ["image/webp"], // Support WebP format
  },
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
