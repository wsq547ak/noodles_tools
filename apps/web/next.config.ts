import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";
const basePath = isProduction ? "/tools" : "";

const nextConfig: NextConfig = {
  basePath,
  reactStrictMode: true,
  output: "standalone",
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
  },
};

export default nextConfig;
