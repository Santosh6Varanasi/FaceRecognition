# Video List JSON Parse Error Fix - Bugfix Design

## Overview

The `/api/video/list` endpoint crashes when the Flask backend returns HTML error pages instead of JSON responses. The current implementation unconditionally calls `flaskRes.json()` without validating the Content-Type header, causing a SyntaxError when attempting to parse HTML as JSON. This fix adds Content-Type validation before parsing and provides graceful error handling for non-JSON responses, ensuring the API never crashes and always returns a structured error response to clients.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when the Flask backend returns a non-JSON response (Content-Type is not application/json)
- **Property (P)**: The desired behavior when non-JSON responses are received - the system should detect the Content-Type, avoid calling `.json()`, and return a structured error response
- **Preservation**: Existing JSON response handling, query parameter forwarding, and error handling for unavailable services that must remain unchanged
- **proxyToFlask**: The function in `lib/flask.ts` that forwards requests to the Flask backend and handles network errors
- **flaskRes**: The Response object returned by `proxyToFlask`, which may contain JSON or HTML content
- **Content-Type header**: HTTP header that indicates the media type of the response body (e.g., "application/json" or "text/html")

## Bug Details

### Bug Condition

The bug manifests when the Flask backend returns an HTML error page (typically with Content-Type: text/html) and the Next.js API route attempts to parse it as JSON. The `GET` handler in `app/api/video/list/route.ts` unconditionally calls `flaskRes.json()` without checking the Content-Type header, causing JSON.parse() to fail when encountering HTML content.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type Response (flaskRes)
  OUTPUT: boolean
  
  contentType := input.headers.get("content-type") OR ""
  
  RETURN NOT contentType.includes("application/json")
         AND input.status >= 200
         AND attemptedToParseAsJSON(input)
END FUNCTION
```

### Examples

- **Example 1**: Flask returns 500 error with HTML page
  - Content-Type: "text/html; charset=utf-8"
  - Body: "<!doctype html><html>...</html>"
  - Current behavior: Crashes with SyntaxError
  - Expected behavior: Returns `{ error: "Received non-JSON response from ML service" }` with status 502

- **Example 2**: Flask returns 404 error with HTML page
  - Content-Type: "text/html"
  - Body: "<html><body>Not Found</body></html>"
  - Current behavior: Crashes with SyntaxError
  - Expected behavior: Returns structured error response with status 502

- **Example 3**: Flask returns plain text error
  - Content-Type: "text/plain"
  - Body: "Service temporarily unavailable"
  - Current behavior: Crashes with SyntaxError
  - Expected behavior: Returns structured error response with status 502

- **Edge case**: Flask returns response with no Content-Type header
  - Content-Type: null or undefined
  - Current behavior: Crashes when attempting to parse
  - Expected behavior: Treats as non-JSON and returns structured error response

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Valid JSON responses from Flask must continue to be parsed and forwarded correctly
- Query parameters (page, page_size) must continue to be forwarded to Flask
- Network errors (Flask unavailable) must continue to return 503 with "ML service unavailable" message
- Successful video list responses must continue to be returned with the correct status code

**Scope:**
All inputs that involve valid JSON responses (Content-Type: application/json) should be completely unaffected by this fix. This includes:
- Successful video list responses with status 200
- Flask error responses that are properly formatted as JSON
- Any other JSON responses from the Flask backend

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Missing Content-Type Validation**: The `GET` handler unconditionally calls `flaskRes.json()` without checking if the response is actually JSON
   - Line 16 in `app/api/video/list/route.ts`: `const data = await flaskRes.json();`
   - No validation of the Content-Type header before parsing

2. **Assumption of JSON Responses**: The code assumes Flask always returns JSON, but Flask can return HTML error pages when:
   - Internal server errors occur (500)
   - Routes are not found (404)
   - Unhandled exceptions occur in Flask

3. **Inadequate Error Handling**: The try-catch block catches the SyntaxError but only logs it and returns a generic 500 error, not distinguishing between parsing errors and other errors

4. **No Response Type Checking**: Unlike other API routes that might validate response types, this endpoint directly attempts JSON parsing without any safety checks

## Correctness Properties

Property 1: Bug Condition - Non-JSON Response Handling

_For any_ Response object where the Content-Type header does not include "application/json", the fixed GET handler SHALL check the Content-Type before attempting to parse, skip the `.json()` call, and return a structured error response with status 502 and message "Received non-JSON response from ML service".

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - JSON Response Handling

_For any_ Response object where the Content-Type header includes "application/json", the fixed GET handler SHALL produce exactly the same behavior as the original handler, successfully parsing the JSON and returning it to the client with the correct status code.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `app/api/video/list/route.ts`

**Function**: `GET`

**Specific Changes**:

1. **Add Content-Type Validation**: After receiving the response from `proxyToFlask`, check the Content-Type header
   - Extract the Content-Type header: `const contentType = flaskRes.headers.get("content-type") || "";`
   - Check if it includes "application/json"

2. **Conditional JSON Parsing**: Only call `flaskRes.json()` if the Content-Type is valid
   - If Content-Type includes "application/json": proceed with parsing
   - If Content-Type does NOT include "application/json": skip parsing and return error

3. **Return Structured Error for Non-JSON**: When non-JSON content is detected, return a proper error response
   - Status code: 502 (Bad Gateway - indicates the upstream server returned invalid content)
   - Error message: `{ error: "Received non-JSON response from ML service" }`
   - Log the actual Content-Type for debugging

4. **Preserve Existing Error Handling**: Keep the try-catch block to handle other errors
   - Network errors are already handled by `proxyToFlask` (returns 503)
   - The try-catch should still catch unexpected errors

5. **Add Logging for Debugging**: Log the Content-Type when non-JSON responses are detected
   - Helps diagnose Flask backend issues
   - Example: `console.error("Expected JSON but received Content-Type:", contentType);`

**Pseudocode for the fix**:
```
GET(request):
  TRY
    // Extract query parameters (unchanged)
    page := searchParams.get("page") ?? "1"
    pageSize := searchParams.get("page_size") ?? "20"
    
    // Proxy to Flask (unchanged)
    flaskRes := proxyToFlask(`/api/video/list?page=${page}&page_size=${pageSize}`)
    
    // NEW: Check Content-Type before parsing
    contentType := flaskRes.headers.get("content-type") OR ""
    
    IF NOT contentType.includes("application/json") THEN
      console.error("Expected JSON but received Content-Type:", contentType)
      RETURN NextResponse.json(
        { error: "Received non-JSON response from ML service" },
        { status: 502 }
      )
    END IF
    
    // Parse JSON only if Content-Type is valid (unchanged logic)
    data := await flaskRes.json()
    RETURN NextResponse.json(data, { status: flaskRes.status })
    
  CATCH err
    console.error("GET /api/video/list error:", err)
    RETURN NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    )
  END TRY
END GET
```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code by simulating non-JSON responses from Flask, then verify the fix correctly handles non-JSON responses while preserving existing JSON response handling.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the unfixed code crashes when Flask returns HTML or other non-JSON content.

**Test Plan**: Mock the `proxyToFlask` function to return Response objects with HTML content and text/html Content-Type. Call the GET handler and observe that it throws SyntaxError when attempting to parse HTML as JSON. Run these tests on the UNFIXED code to confirm the bug.

**Test Cases**:
1. **HTML Error Page Test**: Mock Flask returning HTML 500 error with Content-Type: text/html (will fail on unfixed code with SyntaxError)
2. **Plain Text Response Test**: Mock Flask returning plain text with Content-Type: text/plain (will fail on unfixed code with SyntaxError)
3. **Missing Content-Type Test**: Mock Flask returning HTML with no Content-Type header (will fail on unfixed code with SyntaxError)
4. **Malformed HTML Test**: Mock Flask returning incomplete HTML like "<!doctype html><html>" (will fail on unfixed code with SyntaxError)

**Expected Counterexamples**:
- SyntaxError: "Unexpected token '<', "<!doctype "... is not valid JSON"
- The error occurs at the line `const data = await flaskRes.json();`
- Possible causes: missing Content-Type validation, unconditional JSON parsing, assumption that Flask always returns JSON

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (non-JSON responses), the fixed function produces the expected behavior (returns structured error without crashing).

**Pseudocode:**
```
FOR ALL flaskRes WHERE isBugCondition(flaskRes) DO
  result := GET_fixed(request_with_mocked_proxyToFlask(flaskRes))
  ASSERT result.status = 502
  ASSERT result.body.error = "Received non-JSON response from ML service"
  ASSERT no exception thrown
END FOR
```

**Test Cases**:
1. **HTML 500 Error**: Verify fixed code returns 502 with structured error
2. **HTML 404 Error**: Verify fixed code returns 502 with structured error
3. **Plain Text Response**: Verify fixed code returns 502 with structured error
4. **No Content-Type Header**: Verify fixed code returns 502 with structured error

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (valid JSON responses), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL flaskRes WHERE NOT isBugCondition(flaskRes) DO
  ASSERT GET_original(request) = GET_fixed(request)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all valid JSON responses

**Test Plan**: Observe behavior on UNFIXED code first for valid JSON responses, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Successful Video List Response**: Mock Flask returning valid JSON with status 200, verify fixed code returns same data and status
2. **Empty Video List Response**: Mock Flask returning empty array JSON, verify fixed code handles it identically
3. **Paginated Response**: Mock Flask returning paginated JSON with page metadata, verify fixed code forwards it correctly
4. **Flask JSON Error Response**: Mock Flask returning JSON error (e.g., `{"error": "Invalid page"}` with status 400), verify fixed code forwards it correctly
5. **Query Parameter Forwarding**: Verify page and page_size parameters are still forwarded correctly to Flask
6. **Flask Unavailable (503)**: Verify the existing 503 error handling from `proxyToFlask` still works

### Unit Tests

- Test Content-Type validation logic with various Content-Type values
- Test that HTML responses return 502 error without crashing
- Test that JSON responses are parsed and returned correctly
- Test edge cases: missing Content-Type, empty Content-Type, Content-Type with charset
- Test that query parameters are forwarded correctly
- Test that Flask unavailable errors (503) are handled correctly

### Property-Based Tests

- Generate random valid JSON responses with various status codes and verify they are handled identically to the original code
- Generate random Content-Type headers (non-JSON) and verify all return 502 error without crashing
- Generate random query parameter combinations and verify they are forwarded correctly
- Test across many scenarios to ensure no regression in JSON handling

### Integration Tests

- Test full request flow with mocked Flask backend returning HTML errors
- Test full request flow with mocked Flask backend returning valid JSON
- Test switching between successful JSON responses and HTML error responses
- Test that the API never crashes regardless of Flask response type
- Test logging output to ensure Content-Type mismatches are logged for debugging
