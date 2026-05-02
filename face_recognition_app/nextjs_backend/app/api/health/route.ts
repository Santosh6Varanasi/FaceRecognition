import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { query } from "@/lib/db";
import { withLogging } from "@/lib/api-logger";

export const GET = withLogging(async (request: NextRequest): Promise<NextResponse> => {
  let flask_reachable = false;
  let db_connected = false;

  try {
    // Extract correlation ID from request headers
    const correlationId = request.headers.get('x-correlation-id') || undefined;
    
    const flaskResponse = await proxyToFlask("/api/health", undefined, correlationId);
    flask_reachable = flaskResponse.ok;
  } catch {
    flask_reachable = false;
  }

  try {
    await query("SELECT 1");
    db_connected = true;
  } catch {
    db_connected = false;
  }

  return NextResponse.json({
    status: "ok",
    flask_reachable,
    db_connected,
  });
});
