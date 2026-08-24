import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const origin = process.env.API_ORIGIN || "http://127.0.0.1:8000";
    return [{ source: "/backend/:path*", destination: `${origin}/:path*` }];
  },
};

export default nextConfig;
