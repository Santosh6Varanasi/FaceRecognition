import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { getCorsHeaders } from "@/lib/cors";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: getCorsHeaders() });
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ job_id: string }> }
): Promise<Response> {
  const { job_id } = await params;
  return proxyToFlask(`/api/model/retrain/status/${job_id}`);
}
