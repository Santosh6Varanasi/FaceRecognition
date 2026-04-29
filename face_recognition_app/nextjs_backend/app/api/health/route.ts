import { NextResponse } from "next/server";
import { proxyToFlask } from "@/lib/flask";
import { query } from "@/lib/db";

export async function GET(): Promise<NextResponse> {
  let flask_reachable = false;
  let db_connected = false;

  try {
    const flaskResponse = await proxyToFlask("/api/health");
    flask_reachable = flaskResponse.ok;
  } catch {
    flask_reachable = false;
  }

  try {
    await query("SELECT 1");
    db_connected = true;
  } catch {
    db_connected = false;
  }

  return NextResponse.json({
    status: "ok",
    flask_reachable,
    db_connected,
  });
}
