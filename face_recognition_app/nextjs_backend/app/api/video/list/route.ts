import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const { searchParams } = new URL(request.url);
    const page = searchParams.get("page") ?? "1";
    const pageSize = searchParams.get("page_size") ?? "20";

    const flaskRes = await proxyToFlask(
      `/api/videos/list?page=${page}&page_size=${pageSize}`
    );

    // Check Content-Type before parsing
    const contentType = flaskRes.headers.get("content-type") || "";
    
    if (!contentType.includes("application/json")) {
      console.error("Expected JSON but received Content-Type:", contentType);
      return NextResponse.json(
        { error: "Received non-JSON response from ML service" },
        { status: 502 }
      );
    }

    const data = await flaskRes.json();
    return NextResponse.json(data, { status: flaskRes.status });
  } catch (err) {
    console.error("GET /api/videos/list error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
