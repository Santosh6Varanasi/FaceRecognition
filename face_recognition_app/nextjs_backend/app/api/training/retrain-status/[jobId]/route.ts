import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function GET(
  request: NextRequest,
  { params }: { params: { jobId: string } }
): Promise<Response> {
  return proxyToFlask(`/api/training/retrain-status/${params.jobId}`, {
    method: "GET",
  });
}
