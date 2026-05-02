import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { getCorsHeaders } from "@/lib/cors";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: getCorsHeaders() });
}

export async function GET(request: NextRequest): Promise<Response> {
  return proxyToFlask("/api/model/versions");
}

