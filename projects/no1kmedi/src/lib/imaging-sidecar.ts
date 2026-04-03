/**
 * Optional FastAPI imaging sidecar. Set IMAGING_SIDECAR_URL to proxy DICOM flows.
 */
export function hasImagingSidecar(): boolean {
  return !!process.env.IMAGING_SIDECAR_URL?.trim();
}

export async function sidecarIngestDicom(_formData: FormData): Promise<unknown> {
  throw new Error("Imaging sidecar ingest is not wired in this build.");
}

export async function sidecarAnalyzeStudy(_studyId: string, _priority: string): Promise<{ analysisJobId: string }> {
  throw new Error("Imaging sidecar analyze is not wired in this build.");
}

export async function sidecarGetJob(_jobId: string): Promise<unknown> {
  throw new Error("Imaging sidecar job lookup is not wired in this build.");
}

export async function sidecarGetMetadata(_studyId: string): Promise<unknown> {
  throw new Error("Imaging sidecar metadata is not wired in this build.");
}

export async function sidecarGetReport(_studyId: string): Promise<unknown> {
  throw new Error("Imaging sidecar report is not wired in this build.");
}

export async function sidecarSignoffStudy(
  _studyId: string,
  _reviewedBy: string
): Promise<{ signedOffAt: string; reviewedBy: string }> {
  throw new Error("Imaging sidecar sign-off is not wired in this build.");
}
