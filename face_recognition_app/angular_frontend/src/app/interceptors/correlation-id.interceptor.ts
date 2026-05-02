import { HttpInterceptorFn } from '@angular/common/http';

/**
 * HTTP interceptor that adds a correlation ID to all outgoing requests.
 * The correlation ID helps trace requests across the entire system (Angular -> Next.js -> Flask).
 * 
 * Format: angular-{timestamp}-{random}
 */
export const correlationIdInterceptor: HttpInterceptorFn = (req, next) => {
  const correlationId = generateCorrelationId('angular');
  
  const clonedReq = req.clone({
    setHeaders: {
      'X-Correlation-ID': correlationId
    }
  });
  
  console.log(`[${correlationId}] Request: ${req.method} ${req.url}`);
  
  return next(clonedReq);
};

/**
 * Generates a unique correlation ID for request tracing.
 * 
 * @param service - The service name (e.g., 'angular', 'nextjs', 'flask')
 * @returns A correlation ID in the format: {service}-{timestamp}-{random}
 */
function generateCorrelationId(service: string): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 10);
  return `${service}-${timestamp}-${random}`;
}
