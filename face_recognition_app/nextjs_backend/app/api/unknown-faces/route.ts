import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function GET(request: NextRequest): Promise<Response> {
  const { searchParams } = request.nextUrl;
  const params = new URLSearchParams();

  const status = searchParams.get("status");
  const page = searchParams.get("page");
  const page_size = searchParams.get("page_size");

  if (status) params.set("status", status);
  if (page) params.set("page", page);
  if (page_size) params.set("page_size", page_size);

  const qs = params.toString();
  return proxyToFlask(`/api/unknown-faces${qs ? `?${qs}` : ""}`);
}
