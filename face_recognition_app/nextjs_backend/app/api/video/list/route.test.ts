import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';
import { GET } from './route';
import * as flask from '@/lib/flask';
import * as fc from 'fast-check';

/**
 * Bug Condition Exploration Test
 * 
 * **Validates: Requirements 1.1, 1.2, 1.3**
 * 
 * CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
 * 
 * Property 1: Bug Condition - Non-JSON Response Causes Crash
 * 
 * This test encodes the EXPECTED behavior after the fix:
 * - When Flask returns non-JSON responses (HTML, plain text, etc.)
 * - The handler should return status 502 with structured error message
 * - No SyntaxError should be thrown
 * 
 * On UNFIXED code, this test will FAIL with:
 * - SyntaxError: "Unexpected token '<', "<!doctype "... is not valid JSON"
 * - This failure PROVES the bug exists
 * 
 * After the fix is implemented, this test will PASS, confirming the bug is fixed.
 */

describe('Bug Condition Exploration: Non-JSON Response Handling', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Test Case 1: HTML 500 Error Response
   * 
   * Simulates Flask returning an HTML error page with 500 status.
   * This is the most common scenario that triggers the bug.
   */
  it('should handle HTML 500 error response without crashing', async () => {
    // Mock proxyToFlask to return HTML content
    const htmlContent = '<!doctype html><html><body><h1>Internal Server Error</h1></body></html>';
    const mockResponse = new Response(htmlContent, {
      status: 500,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    // Create a mock request
    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    // Call the GET handler
    // EXPECTED ON UNFIXED CODE: This will throw SyntaxError when trying to parse HTML as JSON
    // EXPECTED AFTER FIX: This will return 502 with structured error message
    const response = await GET(request);
    const data = await response.json();

    // Assert expected behavior (after fix)
    expect(response.status).toBe(502);
    expect(data).toEqual({ error: 'Received non-JSON response from ML service' });
  });

  /**
   * Test Case 2: HTML 404 Error Response
   * 
   * Simulates Flask returning an HTML 404 page.
   */
  it('should handle HTML 404 error response without crashing', async () => {
    const htmlContent = '<html><body><h1>404 Not Found</h1></body></html>';
    const mockResponse = new Response(htmlContent, {
      status: 404,
      headers: { 'Content-Type': 'text/html' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    // EXPECTED ON UNFIXED CODE: SyntaxError
    // EXPECTED AFTER FIX: 502 with structured error
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(502);
    expect(data).toEqual({ error: 'Received non-JSON response from ML service' });
  });

  /**
   * Test Case 3: Plain Text Response
   * 
   * Simulates Flask returning plain text instead of JSON.
   */
  it('should handle plain text response without crashing', async () => {
    const textContent = 'Service temporarily unavailable';
    const mockResponse = new Response(textContent, {
      status: 503,
      headers: { 'Content-Type': 'text/plain' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    // EXPECTED ON UNFIXED CODE: SyntaxError
    // EXPECTED AFTER FIX: 502 with structured error
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(502);
    expect(data).toEqual({ error: 'Received non-JSON response from ML service' });
  });

  /**
   * Test Case 4: Missing Content-Type Header
   * 
   * Simulates Flask returning HTML with no Content-Type header.
   * This is an edge case that should also be handled gracefully.
   */
  it('should handle response with missing Content-Type header without crashing', async () => {
    const htmlContent = '<!doctype html><html><body>Error</body></html>';
    const mockResponse = new Response(htmlContent, {
      status: 500,
      headers: {}, // No Content-Type header
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    // EXPECTED ON UNFIXED CODE: SyntaxError
    // EXPECTED AFTER FIX: 502 with structured error
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(502);
    expect(data).toEqual({ error: 'Received non-JSON response from ML service' });
  });

  /**
   * Test Case 5: Malformed HTML
   * 
   * Simulates Flask returning incomplete/malformed HTML.
   * This tests the robustness of the fix.
   */
  it('should handle malformed HTML response without crashing', async () => {
    const malformedHtml = '<!doctype html><html>';
    const mockResponse = new Response(malformedHtml, {
      status: 500,
      headers: { 'Content-Type': 'text/html' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    // EXPECTED ON UNFIXED CODE: SyntaxError
    // EXPECTED AFTER FIX: 502 with structured error
    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(502);
    expect(data).toEqual({ error: 'Received non-JSON response from ML service' });
  });
});

/**
 * Preservation Property Tests
 * 
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
 * 
 * Property 2: Preservation - Valid JSON Response Handling
 * 
 * These tests verify that valid JSON responses from Flask continue to be handled
 * correctly. They follow the observation-first methodology:
 * 1. Run tests on UNFIXED code to observe baseline behavior
 * 2. Tests should PASS on unfixed code (confirming current JSON handling works)
 * 3. After fix is implemented, tests should still PASS (confirming no regression)
 * 
 * These tests use property-based testing to generate many test cases and provide
 * stronger guarantees that JSON response handling is preserved across all scenarios.
 */

describe('Preservation: Valid JSON Response Handling', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Test Case 1: Successful Video List Response (200)
   * 
   * Verifies that valid JSON responses with status 200 are parsed and returned correctly.
   */
  it('should handle successful video list response with status 200', async () => {
    const videoListData = {
      videos: [
        { id: 1, filename: 'video1.mp4', upload_date: '2024-01-01' },
        { id: 2, filename: 'video2.mp4', upload_date: '2024-01-02' },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    };

    const mockResponse = new Response(JSON.stringify(videoListData), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    const response = await GET(request);
    const data = await response.json();

    // Assert that JSON is parsed and returned correctly
    expect(response.status).toBe(200);
    expect(data).toEqual(videoListData);
  });

  /**
   * Test Case 2: Empty Video List Response (200)
   * 
   * Verifies that empty JSON arrays are handled correctly.
   */
  it('should handle empty video list response', async () => {
    const emptyListData = {
      videos: [],
      total: 0,
      page: 1,
      page_size: 20,
    };

    const mockResponse = new Response(JSON.stringify(emptyListData), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data).toEqual(emptyListData);
  });

  /**
   * Test Case 3: Paginated Response
   * 
   * Verifies that paginated JSON responses with metadata are handled correctly.
   */
  it('should handle paginated response with metadata', async () => {
    const paginatedData = {
      videos: [
        { id: 21, filename: 'video21.mp4', upload_date: '2024-01-21' },
        { id: 22, filename: 'video22.mp4', upload_date: '2024-01-22' },
      ],
      total: 100,
      page: 2,
      page_size: 20,
      total_pages: 5,
    };

    const mockResponse = new Response(JSON.stringify(paginatedData), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=2&page_size=20');

    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data).toEqual(paginatedData);
  });

  /**
   * Test Case 4: JSON Error Response (400)
   * 
   * Verifies that JSON error responses from Flask are forwarded correctly.
   */
  it('should handle JSON error response with status 400', async () => {
    const errorData = {
      error: 'Invalid page parameter',
      details: 'Page must be a positive integer',
    };

    const mockResponse = new Response(JSON.stringify(errorData), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=-1&page_size=20');

    const response = await GET(request);
    const data = await response.json();

    // Assert that Flask error responses are forwarded with correct status
    expect(response.status).toBe(400);
    expect(data).toEqual(errorData);
  });

  /**
   * Test Case 5: Query Parameter Forwarding
   * 
   * Verifies that query parameters (page, page_size) are forwarded correctly to Flask.
   */
  it('should forward query parameters correctly to Flask', async () => {
    const videoListData = {
      videos: [],
      total: 0,
      page: 3,
      page_size: 50,
    };

    const mockResponse = new Response(JSON.stringify(videoListData), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

    const proxyToFlaskSpy = vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=3&page_size=50');

    await GET(request);

    // Assert that proxyToFlask was called with correct query parameters
    expect(proxyToFlaskSpy).toHaveBeenCalledWith('/api/videos/list?page=3&page_size=50');
  });

  /**
   * Test Case 6: Default Query Parameters
   * 
   * Verifies that default values are used when query parameters are not provided.
   */
  it('should use default query parameters when not provided', async () => {
    const videoListData = {
      videos: [],
      total: 0,
      page: 1,
      page_size: 20,
    };

    const mockResponse = new Response(JSON.stringify(videoListData), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });

    const proxyToFlaskSpy = vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list');

    await GET(request);

    // Assert that default values (page=1, page_size=20) are used
    expect(proxyToFlaskSpy).toHaveBeenCalledWith('/api/videos/list?page=1&page_size=20');
  });

  /**
   * Test Case 7: Flask Unavailable (503)
   * 
   * Verifies that the existing 503 error handling from proxyToFlask still works.
   * When Flask is unavailable, proxyToFlask returns a 503 response with JSON error.
   */
  it('should handle Flask unavailable error (503)', async () => {
    const unavailableResponse = new Response(
      JSON.stringify({ error: 'ML service unavailable. Please try again later.' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(unavailableResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    const response = await GET(request);
    const data = await response.json();

    // Assert that 503 errors are handled correctly
    expect(response.status).toBe(503);
    expect(data).toEqual({ error: 'ML service unavailable. Please try again later.' });
  });

  /**
   * Test Case 8: Content-Type with Charset
   * 
   * Verifies that JSON responses with charset in Content-Type are handled correctly.
   */
  it('should handle JSON response with charset in Content-Type', async () => {
    const videoListData = {
      videos: [{ id: 1, filename: 'video1.mp4' }],
      total: 1,
    };

    const mockResponse = new Response(JSON.stringify(videoListData), {
      status: 200,
      headers: { 'Content-Type': 'application/json; charset=utf-8' },
    });

    vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

    const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

    const response = await GET(request);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data).toEqual(videoListData);
  });
});

/**
 * Property-Based Preservation Tests
 * 
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
 * 
 * These property-based tests use fast-check to generate many test cases automatically,
 * providing stronger guarantees that JSON response handling is preserved across all
 * scenarios. They test universal properties that should hold for all valid JSON responses.
 */

describe('Property-Based Preservation Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Property Test 1: All Valid JSON Responses Are Parsed Correctly
   * 
   * For ANY valid JSON response with Content-Type: application/json,
   * the handler should parse and return the JSON data with the correct status code.
   */
  it('should parse and return any valid JSON response correctly', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary JSON-serializable objects
        fc.record({
          videos: fc.array(
            fc.record({
              id: fc.integer({ min: 1, max: 10000 }),
              filename: fc.string({ minLength: 1, maxLength: 50 }),
              upload_date: fc.constantFrom('2024-01-01', '2024-01-15', '2024-02-20', '2024-03-10'),
            })
          ),
          total: fc.integer({ min: 0, max: 10000 }),
          page: fc.integer({ min: 1, max: 100 }),
          page_size: fc.integer({ min: 1, max: 100 }),
        }),
        // Generate various success status codes
        fc.constantFrom(200, 201),
        async (jsonData, statusCode) => {
          const mockResponse = new Response(JSON.stringify(jsonData), {
            status: statusCode,
            headers: { 'Content-Type': 'application/json' },
          });

          vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

          const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

          const response = await GET(request);
          const data = await response.json();

          // Property: Response status matches Flask status
          expect(response.status).toBe(statusCode);
          // Property: Response data matches Flask data exactly
          expect(data).toEqual(jsonData);
        }
      ),
      { numRuns: 50 } // Run 50 random test cases
    );
  });

  /**
   * Property Test 2: All JSON Error Responses Are Forwarded Correctly
   * 
   * For ANY JSON error response (4xx, 5xx) with Content-Type: application/json,
   * the handler should forward the error with the correct status code.
   */
  it('should forward any JSON error response with correct status code', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary error objects
        fc.record({
          error: fc.string({ minLength: 1, maxLength: 100 }),
          details: fc.option(fc.string({ minLength: 1, maxLength: 200 }), { nil: undefined }),
        }),
        // Generate various error status codes
        fc.constantFrom(400, 401, 403, 404, 422, 500, 502, 503),
        async (errorData, statusCode) => {
          const mockResponse = new Response(JSON.stringify(errorData), {
            status: statusCode,
            headers: { 'Content-Type': 'application/json' },
          });

          vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

          const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

          const response = await GET(request);
          const data = await response.json();

          // Property: Error status is preserved
          expect(response.status).toBe(statusCode);
          // Property: Error data is forwarded exactly
          expect(data).toEqual(errorData);
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Property Test 3: Query Parameters Are Always Forwarded Correctly
   * 
   * For ANY valid page and page_size parameters, they should be forwarded to Flask.
   */
  it('should forward any valid query parameters to Flask', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 1000 }),
        fc.integer({ min: 1, max: 200 }),
        async (page, pageSize) => {
          const mockResponse = new Response(JSON.stringify({ videos: [], total: 0 }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          });

          const proxyToFlaskSpy = vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

          const request = new NextRequest(
            `http://localhost:3000/api/video/list?page=${page}&page_size=${pageSize}`
          );

          await GET(request);

          // Property: Query parameters are forwarded exactly as provided
          expect(proxyToFlaskSpy).toHaveBeenCalledWith(
            `/api/videos/list?page=${page}&page_size=${pageSize}`
          );
        }
      ),
      { numRuns: 50 }
    );
  });

  /**
   * Property Test 4: Content-Type Variations Are Handled
   * 
   * For ANY Content-Type that includes "application/json" (with or without charset),
   * the handler should parse the JSON correctly.
   */
  it('should handle any Content-Type variation that includes application/json', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          videos: fc.array(fc.record({ id: fc.integer(), filename: fc.string() })),
          total: fc.integer({ min: 0 }),
        }),
        fc.constantFrom(
          'application/json',
          'application/json; charset=utf-8',
          'application/json; charset=UTF-8',
          'application/json;charset=utf-8'
        ),
        async (jsonData, contentType) => {
          const mockResponse = new Response(JSON.stringify(jsonData), {
            status: 200,
            headers: { 'Content-Type': contentType },
          });

          vi.spyOn(flask, 'proxyToFlask').mockResolvedValue(mockResponse);

          const request = new NextRequest('http://localhost:3000/api/video/list?page=1&page_size=20');

          const response = await GET(request);
          const data = await response.json();

          // Property: All Content-Type variations with application/json work
          expect(response.status).toBe(200);
          expect(data).toEqual(jsonData);
        }
      ),
      { numRuns: 30 }
    );
  });
});
