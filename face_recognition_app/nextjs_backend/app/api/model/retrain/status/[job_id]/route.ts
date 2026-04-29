import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function GET(
  _request: NextRequest,
  { params }: { params: { job_id: string } }
): Promise<Response> {
  return proxyToFlask(`/api/model/retrain/status/${params.job_id}`);
}
