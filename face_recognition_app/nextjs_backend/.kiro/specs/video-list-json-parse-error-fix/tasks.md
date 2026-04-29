# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Non-JSON Response Causes Crash
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Mock `proxyToFlask` to return Response objects with HTML content (Content-Type: text/html)
  - Test cases: HTML 500 error, HTML 404 error, plain text response, missing Content-Type header
  - Assert that the GET handler returns status 502 with error message "Received non-JSON response from ML service"
  - Assert that no SyntaxError is thrown (expected behavior after fix)
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS with SyntaxError: "Unexpected token '<', "<!doctype "... is not valid JSON" (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Valid JSON Response Handling
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for valid JSON responses (Content-Type: application/json)
  - Mock `proxyToFlask` to return valid JSON responses with various status codes (200, 400, etc.)
  - Test cases: successful video list (200), empty list (200), paginated response, JSON error response (400), query parameter forwarding
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Assert that JSON responses are parsed and returned with correct status codes
  - Assert that query parameters (page, page_size) are forwarded correctly
  - Assert that Flask unavailable errors (503) are handled correctly
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for JSON parsing error in video list API

  - [x] 3.1 Implement the fix in app/api/video/list/route.ts
    - Add Content-Type validation after receiving response from proxyToFlask
    - Extract Content-Type header: `const contentType = flaskRes.headers.get("content-type") || "";`
    - Check if Content-Type includes "application/json"
    - If Content-Type does NOT include "application/json", skip JSON parsing and return structured error
    - Return status 502 with error message: `{ error: "Received non-JSON response from ML service" }`
    - Log the actual Content-Type for debugging: `console.error("Expected JSON but received Content-Type:", contentType);`
    - Only call `flaskRes.json()` if Content-Type is valid
    - Preserve existing try-catch block for other errors
    - Preserve existing query parameter forwarding logic
    - _Bug_Condition: isBugCondition(flaskRes) where NOT contentType.includes("application/json") AND flaskRes.status >= 200 AND attemptedToParseAsJSON(flaskRes)_
    - _Expected_Behavior: For non-JSON responses, return status 502 with structured error message without crashing_
    - _Preservation: Valid JSON responses (Content-Type: application/json) must continue to be parsed and forwarded correctly; query parameters must continue to be forwarded; network errors must continue to return 503_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Non-JSON Response Handled Gracefully
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed - no more SyntaxError, returns 502 with structured error)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Valid JSON Response Handling Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions - JSON responses still handled correctly)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
