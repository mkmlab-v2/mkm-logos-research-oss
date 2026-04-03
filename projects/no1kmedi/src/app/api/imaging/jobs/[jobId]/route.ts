import { NextRequest, NextResponse } from 'next/server'
import { getJobStatus } from '@/lib/imaging-store'
import { hasImagingSidecar, sidecarGetJob } from '@/lib/imaging-sidecar'

/**
 * GET /api/imaging/jobs/:jobId
 * Returns mock status for an imaging ingest/analyze job.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> }
) {
  const { jobId } = await params

  if (hasImagingSidecar()) {
    try {
      const status = await sidecarGetJob(jobId)
      return NextResponse.json(status)
    } catch (error: any) {
      return NextResponse.json(
        { success: false, error: error?.message ?? 'Sidecar job lookup failed.' },
        { status: 502 }
      )
    }
  }

  const status = getJobStatus(jobId)

  if (!status) {
    return NextResponse.json(
      { success: false, error: 'Job not found.' },
      { status: 404 }
    )
  }

  return NextResponse.json(status)
}
