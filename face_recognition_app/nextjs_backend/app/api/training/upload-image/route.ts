import { NextRequest, NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function POST(request: NextRequest): Promise<Response> {
  // Forward multipart form data directly to Flask
  const formData = await request.formData();
  
  // Convert FormData to a format fetch can send
  const flaskFormData = new FormData();
  const imageFile = formData.get('image');
  if (imageFile) {
    flaskFormData.append('image', imageFile);
  }
  
  return proxyToFlask("/api/training/upload-image", {
    method: "POST",
    body: flaskFormData,
  });
}
