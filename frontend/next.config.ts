import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pins the workspace root to this project so Turbopack doesn't get confused
  // by an unrelated lockfile higher up in the filesystem (e.g. C:\Users\<you>).
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
