import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    // Forward the raw multipart body to Flask, preserving the Content-Type
    // header (which includes the multipart boundary).
    const contentType = request.headers.get("content-type") ?? "";
    const body = await request.arrayBuffer();

    const flaskRes = await proxyToFlask("/api/videos/upload", {
      method: "POST",
      headers: { "Content-Type": contentType },
      body,
    });

    const data = await flaskRes.json();
    return NextResponse.json(data, { status: flaskRes.status });
  } catch (err) {
    console.error("POST /api/videos/upload error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
