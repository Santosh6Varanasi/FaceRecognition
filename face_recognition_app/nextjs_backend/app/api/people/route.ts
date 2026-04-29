import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}

export async function GET(): Promise<NextResponse> {
  try {
    const result = await query(
      `SELECT p.id, p.name, p.description, p.role, p.created_at,
              COUNT(f.id)::int AS face_count
       FROM people p
       LEFT JOIN faces f ON p.id = f.person_id
       GROUP BY p.id
       ORDER BY p.name`
    );
    return NextResponse.json(result.rows);
  } catch (err) {
    console.error("GET /api/people error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  try {
    const body = await request.json();
    const { name, description = null, role = null } = body as {
      name: string;
      description?: string | null;
      role?: string | null;
    };

    const result = await query(
      `INSERT INTO people (name, description, role)
       VALUES ($1, $2, $3)
       RETURNING *`,
      [name, description, role]
    );

    return NextResponse.json(result.rows[0], { status: 201 });
  } catch (err: unknown) {
    const pgErr = err as { code?: string };
    if (pgErr?.code === "23505") {
      return NextResponse.json(
        { error: "Person already exists" },
        { status: 409 }
      );
    }
    console.error("POST /api/people error:", err);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
