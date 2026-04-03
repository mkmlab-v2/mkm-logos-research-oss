import { NextRequest, NextResponse } from 'next/server'
import { createAnalysisJob } from '@/lib/imaging-store'
import { hasImagingSidecar, sidecarAnalyzeStudy } from '@/lib/imaging-sidecar'

/**
 * POST /api/imaging/studies/:studyId/analyze
 * Triggers assistive imaging analysis for a study.
 */
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ studyId: string }> }
) {
  try {
    const { studyId } = await params
    const body = await request.json().catch(() => ({}))
    const priority = body?.priority ?? 'standard'

    if (hasImagingSidecar()) {
      try {
        const analysis = await sidecarAnalyzeStudy(studyId, priority)
        return NextResponse.json(
          {
            success: true,
            studyId,
            analysisJobId: analysis.analysisJobId,
            status: 'queued',
            priority,
          },
          { status: 202 }
        )
      } catch (error: any) {
        return NextResponse.json(
          { success: false, error: error?.message ?? 'Sidecar analyze failed.' },
          { status: 502 }
        )
      }
    }

    const analysis = createAnalysisJob(studyId)
    if (!analysis) {
      return NextResponse.json(
        { success: false, error: 'Study not found.' },
        { status: 404 }
      )
    }

    return NextResponse.json(
      {
        success: true,
        studyId,
        analysisJobId: analysis.analysisJobId,
        status: 'queued',
        priority
      },
      { status: 202 }
    )
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: `Analyze request failed: ${error?.message ?? 'unknown error'}` },
      { status: 500 }
    )
  }
}
