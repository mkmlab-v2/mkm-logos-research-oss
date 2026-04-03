export type DicomIngestResponse = {
  success: boolean;
  jobId: string;
  studyId: string;
  status: string;
  message: string;
};
