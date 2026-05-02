/**
 * Angular Environment Configuration
 * 
 * This file is replaced during build based on the target environment.
 * The apiBaseUrl should point to the Next.js backend, not Flask directly.
 * 
 * For development: http://localhost:3000 (Next.js)
 * For production: Create environment.prod.ts with production values
 * 
 * Note: Angular runs in the browser and doesn't have access to Node.js process.env
 * Environment-specific values should be set in separate environment files:
 * - environment.ts (development)
 * - environment.prod.ts (production)
 * - environment.staging.ts (staging)
 */

export const environment = {
  production: false,
  // Angular should call Next.js backend (port 3000), not Flask (port 5000) directly
  apiBaseUrl: 'http://localhost:3000'
};
