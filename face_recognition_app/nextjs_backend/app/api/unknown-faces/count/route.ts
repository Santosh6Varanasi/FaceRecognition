import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { getCorsHeaders } from "@/lib/cors";
import { withLogging } from "@/lib/api-logger";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: getCorsHeaders() });
}

export const GET = withLogging(async (request: NextRequest): Promise<NextResponse> => {
  try {
    const { searchParams } = new URL(request.url);
    const filterStatus = searchParams.get("filter_status") || "all";
    const correlationId = request.headers.get('x-correlation-id') || undefined;
    
    const flaskRes = await proxyToFlask(
      `/api/unknown-faces/count?filter_status=${filterStatus}`,
      undefined,
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
