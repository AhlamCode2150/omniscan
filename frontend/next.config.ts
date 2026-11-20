import type { NextConfig } from "next";

const API = process.env.OMNISCAN_API_URL || "http://127.0.0.1:8000";

const config: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/api/:path*` }];
  },
  experimental: { proxyTimeout: 600_000 },
};
export default config;
