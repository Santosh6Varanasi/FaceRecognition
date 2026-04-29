# Bugfix Requirements Document

## Introduction

The `/api/video/list` endpoint crashes with a SyntaxError when the Flask backend returns HTML error pages instead of JSON responses. This occurs because the endpoint unconditionally attempts to parse the response as JSON without checking the Content-Type header. The fix ensures graceful handling of non-JSON responses and prevents crashes when the Flask backend encounters errors.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the Flask backend returns an HTML error page (Content-Type: text/html) THEN the system crashes with SyntaxError: "Unexpected token '<', "<!doctype "... is not valid JSON"

1.2 WHEN the Flask backend returns a non-JSON response THEN the system attempts to parse it as JSON without validation

1.3 WHEN `flaskRes.json()` is called on an HTML response THEN the JSON.parse() method fails and throws an unhandled exception

### Expected Behavior (Correct)

2.1 WHEN the Flask backend returns an HTML error page (Content-Type: text/html) THEN the system SHALL check the Content-Type header and return a proper error response without crashing

2.2 WHEN the Flask backend returns a non-JSON response THEN the system SHALL detect this condition and handle it gracefully

2.3 WHEN `flaskRes.json()` would fail due to non-JSON content THEN the system SHALL return a structured error response to the client with appropriate status code

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the Flask backend returns a valid JSON response with Content-Type: application/json THEN the system SHALL CONTINUE TO parse and return the JSON data successfully

3.2 WHEN the Flask backend returns a successful video list response THEN the system SHALL CONTINUE TO forward the data and status code to the client

3.3 WHEN the Flask backend is unavailable (503 error from proxyToFlask) THEN the system SHALL CONTINUE TO return the "ML service unavailable" error message

3.4 WHEN query parameters (page, page_size) are provided THEN the system SHALL CONTINUE TO forward them to the Flask backend correctly
