import { NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function GET(): Promise<Response> {
  return proxyToFlask("/api/model/versions");
}
