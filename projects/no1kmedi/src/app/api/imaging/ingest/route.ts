import { NextRequest, NextResponse } from 'next/server'
import type { DicomIngestResponse } from '@/lib/imaging-contract'
import { createIngestJob } from '@/lib/imaging-store'
import { hasImagingSidecar, sidecarIngestDicom } from '@/lib/imaging-sidecar'

/**
 * POST /api/imaging/ingest
 * Accepts DICOM uploads and creates an imaging ingest job.
 */
export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const files = formData.getAll('files')

    if (!files || files.length === 0) {
      return NextResponse.json(
        { success: false, error: 'No DICOM files were provided.' },
        { status: 400 }
      )
    }

    if (hasImagingSidecar()) {
      const payload = await sidecarIngestDicom(formData)
      return NextResponse.json(payload, { status: 202 })
    }

    const { jobId, studyId } = createIngestJob(files.length)

    const payload: DicomIngestResponse = {
      success: true,
      jobId,
      studyId,
      status: 'queued',
      message: 'Ingest job has been queued.'
    }

    return NextResponse.json(payload, { status: 202 })
  } catch (error: any) {
    console.error('Imaging ingest error:', error)
    return NextResponse.json(
      { success: false, error: `Ingest failed: ${error?.message ?? 'unknown error'}` },
      { status: 500 }
    )
  }
}
