import { NextRequest, NextResponse } from 'next/server'
import { getStudyReport } from '@/lib/imaging-store'
import { hasImagingSidecar, sidecarGetReport } from '@/lib/imaging-sidecar'

/**
 * GET /api/imaging/studies/:studyId/report
 * Returns assistive report draft for clinician review.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ studyId: string }> }
) {
  const { studyId } = await params

  if (hasImagingSidecar()) {
    try {
      const report = await sidecarGetReport(studyId)
      return NextResponse.json({ success: true, report })
    } catch (error: any) {
      return NextResponse.json(
        { success: false, error: error?.message ?? 'Sidecar report lookup failed.' },
        { status: 502 }
      )
    }
  }

  const report = getStudyReport(studyId)

  if (!report) {
    return NextResponse.json(
      { success: false, error: 'Report not found. Run analyze first.' },
      { status: 404 }
    )
  }

  return NextResponse.json({ success: true, report })
}
