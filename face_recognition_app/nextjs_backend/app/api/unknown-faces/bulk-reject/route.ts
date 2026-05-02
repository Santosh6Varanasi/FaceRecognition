import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { getCorsHeaders } from "@/lib/cors";
import { withLogging } from "@/lib/api-logger";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: getCorsHeaders() });
}

export const POST = withLogging(async (request: NextRequest): Promise<NextResponse> => {
  try {
    const body = await request.json();
    const correlationId = request.headers.get('x-correlation-id') || undefined;
    
    const flaskRes = await proxyToFlask(
      `/api/unknown-faces/bulk-reject`,
      { 
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      },
      correlationId
    );

    const data = await flaskRes.json();
    return NextResponse.json(data, { status: flaskRes.status });
  } catch (err) {
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
});
