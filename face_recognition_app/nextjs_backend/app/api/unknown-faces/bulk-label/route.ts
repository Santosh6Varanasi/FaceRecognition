import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { getCorsHeaders } from "@/lib/cors";
import { withLogging } from "@/lib/api-logger";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: getCorsHeaders() });
}

export const POST = withLogging(async (request: NextRequest): Promise<Response> => {
  const body = await request.text();
  return proxyToFlask("/api/unknown-faces/bulk-label", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
});
