import { NextResponse } from "next/server";
import { query } from "@/lib/db";

export async function GET(): Promise<NextResponse> {
  try {
    const [
      peopleResult,
      facesResult,
      pendingResult,
      labeledResult,
      modelResult,
      detectionsResult,
    ] = await Promise.all([
      query("SELECT COUNT(*)::int AS count FROM people"),
      query("SELECT COUNT(*)::int AS count FROM faces"),
      query(
        "SELECT COUNT(*)::int AS count FROM unknown_faces WHERE status = 'pending'"
      ),
      query(
        "SELECT COUNT(*)::int AS count FROM unknown_faces WHERE status = 'labeled'"
      ),
      query(
        `SELECT version_number, cross_validation_accuracy
         FROM model_versions
         WHERE is_active = TRUE
         LIMIT 1`
      ),
      query(
        `SELECT COUNT(*)::int AS count
         FROM detections d
         JOIN frames f ON d.frame_id = f.id
         WHERE f.created_at >= CURRENT_DATE`
      ),
    ]);

    const activeModel = modelResult.rows[0] ?? null;

    return NextResponse.json({
      total_people: peopleResult.rows[0].count,
      total_faces: facesResult.rows[0].count,
      pending_unknowns: pendingResult.rows[0].count,
      labeled_unknowns: labeledResult.rows[0].count,
      active_model_version: activeModel?.version_number ?? null,
      active_model_accuracy: activeModel?.cross_validation_accuracy ?? null,
      total_detections_today: detectionsResult.rows[0].count,
    });
  } catch (err) {
    console.error("GET /api/dashboard/stats error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
