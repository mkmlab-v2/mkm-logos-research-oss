import { NextRequest, NextResponse } from 'next/server'
import { getStudyMetadata } from '@/lib/imaging-store'
import { hasImagingSidecar, sidecarGetMetadata } from '@/lib/imaging-sidecar'

/**
 * GET /api/imaging/studies/:studyId/metadata
 * Returns normalized metadata extracted from DICOM files.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ studyId: string }> }
) {
  const { studyId } = await params

  if (hasImagingSidecar()) {
    try {
      const metadata = await sidecarGetMetadata(studyId)
      return NextResponse.json({ success: true, metadata })
    } catch (error: any) {
      return NextResponse.json(
        { success: false, error: error?.message ?? 'Sidecar metadata lookup failed.' },
        { status: 502 }
      )
    }
  }

  const metadata = getStudyMetadata(studyId)

  if (!metadata) {
    return NextResponse.json(
      { success: false, error: 'Study not found.' },
      { status: 404 }
    )
  }

  return NextResponse.json({ success: true, metadata })
}
