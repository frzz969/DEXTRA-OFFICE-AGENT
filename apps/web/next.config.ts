import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  transpilePackages: ['@dextra/ui', '@dextra/design-system', '@dextra/contracts'],
  experimental: {
    externalDir: true,
  },
};

export default nextConfig;
