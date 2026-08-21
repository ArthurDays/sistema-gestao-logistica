import type { NextConfig } from "next";

const isNetlifyStaticExport =
  process.env.NETLIFY_STATIC_EXPORT === "true";

const nextConfig: NextConfig = {
  output: isNetlifyStaticExport ? "export" : "standalone",
};

export default nextConfig;
