import { NextRequest, NextResponse } from 'next/server'
import { getStudyReport, saveSignoff } from '@/lib/imaging-store'
import { hasImagingSidecar, sidecarSignoffStudy } from '@/lib/imaging-sidecar'

/**
 * POST /api/imaging/studies/:studyId/signoff
 * Stores clinician check-off for finalized assistive report.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ studyId: string }> }
) {
  try {
    const { studyId } = await params
    const body = await request.json()

    if (!body?.reviewedBy || body?.confirmed !== true) {
      return NextResponse.json(
        {
          success: false,
          error: 'reviewedBy and confirmed=true are required for clinician sign-off.'
        },
        { status: 400 }
      )
    }

    if (hasImagingSidecar()) {
      try {
        const signoff = await sidecarSignoffStudy(studyId, body.reviewedBy)
        return NextResponse.json({
          success: true,
          studyId,
          signedOffAt: signoff.signedOffAt,
          reviewedBy: signoff.reviewedBy,
        })
      } catch (error: any) {
        return NextResponse.json(
          { success: false, error: error?.message ?? 'Sidecar sign-off failed.' },
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

    const signoff = saveSignoff(studyId, body.reviewedBy)
    if (!signoff) {
      return NextResponse.json(
        { success: false, error: 'Study not found.' },
        { status: 404 }
      )
    }

    return NextResponse.json({
      success: true,
      studyId,
      signedOffAt: signoff.signedOffAt,
      reviewedBy: signoff.reviewedBy
    })
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: `Sign-off failed: ${error?.message ?? 'unknown error'}` },
      { status: 500 }
    )
  }
}
