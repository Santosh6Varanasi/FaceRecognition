/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Enable new features in Next.js 16
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  logging: {
    fetches: {
      fullUrl: true,
    },
  },
  async headers() {
    // Get CORS configuration from environment variables
    const corsOrigin = process.env.CORS_ORIGINS?.split(',')[0]?.trim() || 'http://localhost:4200';
    const corsMethods = process.env.CORS_METHODS || 'GET,POST,PUT,DELETE,OPTIONS';
    const corsHeaders = process.env.CORS_HEADERS || 'Content-Type,Authorization,X-Correlation-ID';
    const corsMaxAge = process.env.CORS_MAX_AGE || '86400';
    
    return [
      {
        source: "/api/:path*",
        headers: [
          { key: "Access-Control-Allow-Origin", value: corsOrigin },
          { key: "Access-Control-Allow-Methods", value: corsMethods },
          { key: "Access-Control-Allow-Headers", value: corsHeaders },
          { key: "Access-Control-Max-Age", value: corsMaxAge },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
