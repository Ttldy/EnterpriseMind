import { api } from "@/api/client";

export interface PermissionRow {
  id: number;
  subject_type: "ROLE" | "DEPARTMENT";
  subject_value: string;
}

export interface KnowledgeBaseRow {
  id: number;
  name: string;
  domain: string;
  sensitivity: string;
  is_public: boolean;
  permissions: PermissionRow[];
  document_count: number;
}

export interface DocumentRow {
  id: number;
  filename: string;
  status: "PROCESSING" | "READY" | "FAILED";
  sensitivity: string;
  error_message: string | null;
  created_at: string;
}

export interface DocumentAccepted {
  id: number;
  filename: string;
  status: string;
  job_id: string;
}

export interface JobStatus {
  id: string;
  status: string;
  attempts: number;
}

export async function fetchKnowledgeBases(): Promise<
  KnowledgeBaseRow[]
> {
  const response =
    await api.get<KnowledgeBaseRow[]>(
      "/knowledge/bases",
    );
  return response.data;
}

export async function createKnowledgeBase(
  payload: {
    name: string;
    domain: string;
    sensitivity: string;
    is_public: boolean;
  },
): Promise<{ id: number; name: string }> {
  const response = await api.post(
    "/knowledge/bases",
    payload,
  );
  return response.data as {
    id: number;
    name: string;
  };
}

export async function addPermission(
  knowledgeBaseId: number,
  payload: {
    subject_type: "ROLE" | "DEPARTMENT";
    subject_value: string;
  },
): Promise<void> {
  await api.post(
    `/knowledge/bases/${knowledgeBaseId}/permissions`,
    payload,
  );
}

export async function fetchDocuments(
  knowledgeBaseId: number,
): Promise<DocumentRow[]> {
  const response = await api.get<DocumentRow[]>(
    `/knowledge/bases/${knowledgeBaseId}/documents`,
  );
  return response.data;
}

export async function uploadDocument(
  knowledgeBaseId: number,
  file: File,
): Promise<DocumentAccepted> {
  const form = new FormData();
  form.append("file", file);
  const response =
    await api.post<DocumentAccepted>(
      `/knowledge/bases/${knowledgeBaseId}/documents`,
      form,
    );
  return response.data;
}

export async function renameKnowledgeBase(
  knowledgeBaseId: number,
  name: string,
): Promise<{ id: number; name: string }> {
  const response = await api.patch<{
    id: number;
    name: string;
  }>(`/knowledge/bases/${knowledgeBaseId}`, {
    name,
  });
  return response.data;
}

export async function removeKnowledgeBase(
  knowledgeBaseId: number,
): Promise<void> {
  await api.delete(
    `/knowledge/bases/${knowledgeBaseId}`,
  );
}

export async function fetchJob(
  jobId: string,
): Promise<JobStatus> {
  const response = await api.get<JobStatus>(
    `/knowledge/jobs/${jobId}`,
  );
  return response.data;
}

export async function retryJob(
  jobId: string,
): Promise<JobStatus> {
  const response = await api.post<JobStatus>(
    `/knowledge/jobs/${jobId}/retry`,
  );
  return response.data;
}

export async function removeDocument(
  documentId: number,
): Promise<void> {
  await api.delete(
    `/knowledge/documents/${documentId}`,
  );
}
