import { NextRequest, NextResponse } from 'next/server';

/**
 * Generate a correlation ID for request tracing
 * Format: nextjs-{timestamp}-{random}
 */
function generateCorrelationId(): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 10);
  return `nextjs-${timestamp}-${random}`;
}

/**
 * Get CORS configuration from environment variables
 */
function getCorsConfig() {
  return {
    origin: process.env.CORS_ORIGINS?.split(',')[0]?.trim() || 'http://localhost:4200',
    methods: process.env.CORS_METHODS || 'GET,POST,PUT,DELETE,OPTIONS',
    headers: process.env.CORS_HEADERS || 'Content-Type,Authorization,X-Correlation-ID',
    maxAge: process.env.CORS_MAX_AGE || '86400',
  };
}

/**
 * Middleware to extract or generate correlation ID for request tracing
 * and add CORS headers to all API responses
 * Runs on all /api routes
 */
export function middleware(request: NextRequest) {
  const corsConfig = getCorsConfig();
  
  // Handle OPTIONS preflight requests
  if (request.method === 'OPTIONS') {
    return new NextResponse(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': corsConfig.origin,
        'Access-Control-Allow-Methods': corsConfig.methods,
        'Access-Control-Allow-Headers': corsConfig.headers,
        'Access-Control-Max-Age': corsConfig.maxAge,
      },
    });
  }

  // Extract correlation ID from request headers or generate a new one
  const correlationId = request.headers.get('x-correlation-id') || generateCorrelationId();
  
  // Store correlation ID in request for use in API routes
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-correlation-id', correlationId);
  
  // Create response and add CORS + correlation ID headers
  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
  
  // Add CORS headers to all responses
  response.headers.set('Access-Control-Allow-Origin', corsConfig.origin);
  response.headers.set('Access-Control-Allow-Methods', corsConfig.methods);
  response.headers.set('Access-Control-Allow-Headers', corsConfig.headers);
  
  // Add correlation ID to response headers
  response.headers.set('x-correlation-id', correlationId);
  
  return response;
}

// Configure middleware to run on API routes only
export const config = {
  matcher: '/api/:path*',
};
