/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Keeps the build worker's memory footprint small (this machine has 8 GB).
    webpackMemoryOptimizations: true,
  },
};

export default nextConfig;
