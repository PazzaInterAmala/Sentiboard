import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  // Pin the project root so a stray lockfile in a parent folder is not picked up.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
