import { NextRequest } from "next/server";
import { proxyToFlask } from "@/lib/flask";

export async function GET(
  _request: NextRequest,
  { params }: { params: { id: string } }
): Promise<Response> {
  const flaskResponse = await proxyToFlask(
    `/api/unknown-faces/${params.id}/image`
  );

  // If Flask returned an error response, pass it through as-is
  if (!flaskResponse.ok) {
    return flaskResponse;
  }

  const imageBytes = await flaskResponse.arrayBuffer();
  return new Response(imageBytes, {
    status: 200,
    headers: { "Content-Type": "image/jpeg" },
  });
}
