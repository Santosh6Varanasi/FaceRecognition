import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { getCorsHeaders } from "@/lib/cors";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: getCorsHeaders() });
}

export async function POST(request: NextRequest): Promise<Response> {
  const body = await request.text();
  return proxyToFlask("/api/model/retrain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}

