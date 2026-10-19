import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Gera .next/standalone (server.js + deps mínimas) para a imagem
  // Docker do Cloud Run -- ver frontend/Dockerfile.
  output: "standalone",
};

export default nextConfig;
