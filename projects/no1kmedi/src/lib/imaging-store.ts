import crypto from "crypto";

type JobRecord = {
  jobId: string;
  studyId: string;
  status: "queued" | "processing" | "completed" | "failed";
  phase: "ingest" | "analyze";
};

type StudyRecord = {
  studyId: string;
  metadata: Record<string, unknown>;
  report: { draft: string; createdAt: string } | null;
  signoff: { reviewedBy: string; signedOffAt: string } | null;
};

const jobs = new Map<string, JobRecord>();
const studies = new Map<string, StudyRecord>();

function rid(prefix: string) {
  return `${prefix}_${crypto.randomBytes(6).toString("hex")}`;
}

export function createIngestJob(fileCount: number): { jobId: string; studyId: string } {
  const studyId = rid("study");
  const jobId = rid("job");
  studies.set(studyId, {
    studyId,
    metadata: {
      source: "ingest",
      fileCount,
      createdAt: new Date().toISOString(),
    },
    report: null,
    signoff: null,
  });
  jobs.set(jobId, { jobId, studyId, status: "completed", phase: "ingest" });
  return { jobId, studyId };
}

export function getJobStatus(jobId: string) {
  const j = jobs.get(jobId);
  if (!j) return null;
  return {
    success: true,
    jobId: j.jobId,
    studyId: j.studyId,
    status: j.status,
    phase: j.phase,
  };
}

export function getStudyMetadata(studyId: string) {
  return studies.get(studyId)?.metadata ?? null;
}

export function createAnalysisJob(studyId: string): { analysisJobId: string } | null {
  const s = studies.get(studyId);
  if (!s) return null;
  const analysisJobId = rid("analysis");
  s.report = {
    draft: "보조 리포트 초안(데모). 임상 판단은 의료진이 검토합니다.",
    createdAt: new Date().toISOString(),
  };
  jobs.set(analysisJobId, { jobId: analysisJobId, studyId, status: "queued", phase: "analyze" });
  return { analysisJobId };
}

export function getStudyReport(studyId: string) {
  return studies.get(studyId)?.report ?? null;
}

export function saveSignoff(studyId: string, reviewedBy: string) {
  const s = studies.get(studyId);
  if (!s?.report) return null;
  const signedOffAt = new Date().toISOString();
  s.signoff = { reviewedBy, signedOffAt };
  return { reviewedBy, signedOffAt };
}
