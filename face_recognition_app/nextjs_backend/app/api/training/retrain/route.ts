import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function POST(request: NextRequest): Promise<Response> {
  const body = await request.text();
  return proxyToFlask("/api/training/retrain", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}
