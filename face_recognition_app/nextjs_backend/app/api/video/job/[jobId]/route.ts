import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function GET(
  _request: NextRequest,
  { params }: { params: { jobId: string } }
): Promise<NextResponse> {
  try {
    const flaskRes = await proxyToFlask(`/api/videos/job/${params.jobId}`);
    const data = await flaskRes.json();
    return NextResponse.json(data, { status: flaskRes.status });
  } catch (err) {
    console.error(`GET /api/videos/job/${params.jobId} error:`, err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
