/**
 * Browser API client. Talks only to the FastAPI HTTP contract.
 * Do not add PostgreSQL, ranking weights, or ML inference here.
 *
 * Access tokens stay in memory (AuthProvider). Refresh uses the httpOnly cookie
 * with credentials: "include". Do not put tokens in localStorage.
 */

import type { AuthTokenResponse, AuthUser, ProblemDetails } from "@/lib/auth";

export type HealthResponse = {
  status: string;
  service: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail ?? problem.title ?? "Request failed");
    this.name = "ApiError";
    this.status = problem.status;
    this.problem = problem;
  }
}

export function getApiBaseUrl(): string {
  return API_BASE;
}

async function parseProblem(response: Response): Promise<ProblemDetails> {
  try {
    const body = (await response.json()) as ProblemDetails;
    return { ...body, status: body.status ?? response.status };
  } catch {
    return { status: response.status, detail: response.statusText, title: "Error" };
  }
}

type RequestOptions = {
  method?: string;
  json?: unknown;
  accessToken?: string | null;
  csrfToken?: string | null;
  retryOnUnauthorized?: boolean;
};

async function rawRequest(path: string, options: RequestOptions = {}): Promise<Response> {
  const headers = new Headers();
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.accessToken) {
    headers.set("Authorization", `Bearer ${options.accessToken}`);
  }
  if (options.csrfToken) {
    headers.set("X-CSRF-Token", options.csrfToken);
  }
  return fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.json !== undefined ? JSON.stringify(options.json) : undefined,
    credentials: "include",
    cache: "no-store",
  });
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await rawRequest(path, options);
  if (!response.ok) {
    throw new ApiError(await parseProblem(response));
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/api/v1/health");
}

export async function registerAccount(input: {
  email: string;
  password: string;
  role: "candidate" | "recruiter";
  organization_name?: string;
}): Promise<AuthUser> {
  return apiRequest<AuthUser>("/api/v1/auth/register", {
    method: "POST",
    json: input,
  });
}

export async function loginAccount(input: { email: string; password: string }): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    json: input,
  });
}

export async function refreshSession(csrfToken: string | null): Promise<AuthTokenResponse> {
  return apiRequest<AuthTokenResponse>("/api/v1/auth/refresh", {
    method: "POST",
    csrfToken,
  });
}

export async function logoutSession(csrfToken: string | null): Promise<void> {
  await apiRequest<{ message: string }>("/api/v1/auth/logout", {
    method: "POST",
    csrfToken,
  });
}

export async function logoutAllSessions(accessToken: string | null): Promise<void> {
  await apiRequest<{ message: string }>("/api/v1/auth/logout-all", {
    method: "POST",
    accessToken,
  });
}

export async function fetchCurrentUser(accessToken: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/api/v1/auth/me", { accessToken });
}

export type ResumeSummary = {
  id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  parse_status: string;
  parser_version: string | null;
  created_at: string;
  parsed_at: string | null;
  duplicate?: boolean;
};

export async function listResumes(
  candidateId: string,
  accessToken: string,
): Promise<{ items: ResumeSummary[] }> {
  return apiRequest<{ items: ResumeSummary[] }>(`/api/v1/candidates/${candidateId}/resumes`, {
    accessToken,
  });
}

export async function deleteResume(
  candidateId: string,
  resumeId: string,
  accessToken: string,
): Promise<void> {
  await apiRequest<{ message: string }>(`/api/v1/candidates/${candidateId}/resumes/${resumeId}`, {
    method: "DELETE",
    accessToken,
  });
}

export function uploadResume(
  candidateId: string,
  file: File,
  accessToken: string,
  onProgress?: (percent: number) => void,
): Promise<ResumeSummary> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getApiBaseUrl()}/api/v1/candidates/${candidateId}/resumes`);
    xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };
    xhr.onload = () => {
      const parseBody = () => {
        try {
          return JSON.parse(xhr.responseText) as ResumeSummary & ProblemDetails;
        } catch {
          return null;
        }
      };
      if (xhr.status >= 200 && xhr.status < 300) {
        const body = parseBody();
        if (body) {
          resolve(body as ResumeSummary);
          return;
        }
      }
      const problem = parseBody();
      reject(
        new ApiError({
          status: xhr.status,
          detail: problem?.detail ?? xhr.statusText,
          title: problem?.title ?? "Error",
          code: problem?.code,
        }),
      );
    };
    xhr.onerror = () => reject(new Error("Upload failed."));
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export { rawRequest };

export type SkillMention = {
  raw_text: string;
  normalized_text: string;
  source_section?: string | null;
  evidence: string;
  extraction_confidence?: number;
};

export type ProfileDraft = {
  summary: string | null;
  skills: SkillMention[];
  experience: {
    job_title: string | null;
    employer: string | null;
    description: string | null;
    start_date: string | null;
    is_current: boolean;
  }[];
  education: {
    institution: string | null;
    degree: string | null;
    field_of_study: string | null;
  }[];
  projects: { name: string | null; description: string | null; url: string | null }[];
  certifications: { name: string | null; issuing_organization: string | null }[];
  nlp_pipeline_version: string;
  warnings: string[];
};

export type SkillNormalizationResult = {
  raw_text: string;
  normalized_text: string;
  canonical_skill_id: string | null;
  canonical_skill_name: string | null;
  resolution_type: "canonical" | "alias" | "fuzzy" | "unmatched";
  ontology_version: string;
  normalization_confidence: number;
  needs_review: boolean;
  evidence: string;
};

export type ProfileView = {
  id: string;
  profile_version: number;
  confirmation_status: string;
  summary: string | null;
  nlp_pipeline_version: string | null;
  ontology_version: string | null;
  draft: ProfileDraft | null;
  normalized_skills: SkillNormalizationResult[];
};

export async function getProfile(candidateId: string, accessToken: string) {
  return apiRequest<{ confirmed: ProfileView | null; draft: ProfileView | null }>(
    `/api/v1/candidates/${candidateId}/profile`,
    { accessToken },
  );
}

export async function updateProfile(
  candidateId: string,
  accessToken: string,
  payload: { summary?: string },
) {
  return apiRequest<ProfileView>(`/api/v1/candidates/${candidateId}/profile`, {
    method: "PUT",
    accessToken,
    json: payload,
  });
}

export async function confirmProfile(candidateId: string, accessToken: string) {
  return apiRequest<ProfileView>(`/api/v1/candidates/${candidateId}/profile/confirm`, {
    method: "POST",
    accessToken,
  });
}

export type EmbeddingStatus = {
  status: "missing" | "current" | "stale" | "incompatible";
  owner_type: string;
  owner_id: string;
  chunk_type: string;
  model_name: string | null;
  model_version: string | null;
  dimensions: number | null;
  embedding_text_version: string | null;
  content_hash: string | null;
  created_at: string | null;
  reused: boolean;
  processing_job_id?: string | null;
};

export async function getProfileEmbedding(candidateId: string, accessToken: string) {
  return apiRequest<EmbeddingStatus>(`/api/v1/candidates/${candidateId}/profile/embedding`, {
    accessToken,
  });
}

export async function createProfileEmbedding(candidateId: string, accessToken: string) {
  return apiRequest<EmbeddingStatus>(`/api/v1/candidates/${candidateId}/profile/embedding`, {
    method: "POST",
    accessToken,
  });
}

export type JobSummary = {
  id: string;
  title: string;
  status: string;
  organization_id: string;
};

export type JobDetail = {
  id: string;
  title: string;
  description_raw: string;
  status: string;
  location: string | null;
  requirements: {
    id: string;
    confirmation_status: string;
    parser_version: string | null;
    draft: {
      required_skills: SkillMention[];
      preferred_skills: SkillMention[];
      min_years_experience: number | null;
      education_level: string | null;
      location: string | null;
      nlp_pipeline_version: string;
    } | null;
    ontology_version: string | null;
    normalized_required_skills: SkillNormalizationResult[];
    normalized_preferred_skills: SkillNormalizationResult[];
  } | null;
};

export async function listJobs(accessToken: string) {
  return apiRequest<{ items: JobSummary[] }>("/api/v1/jobs", { accessToken });
}

export async function createJob(accessToken: string, payload: { title: string; description_raw: string }) {
  return apiRequest<JobDetail>("/api/v1/jobs", { method: "POST", accessToken, json: payload });
}

export async function getJob(jobId: string, accessToken: string) {
  return apiRequest<JobDetail>(`/api/v1/jobs/${jobId}`, { accessToken });
}

export async function confirmJobRequirements(jobId: string, accessToken: string) {
  return apiRequest<{ confirmation_status: string }>(`/api/v1/jobs/${jobId}/requirements/confirm`, {
    method: "POST",
    accessToken,
  });
}

export async function getJobEmbedding(jobId: string, accessToken: string) {
  return apiRequest<EmbeddingStatus>(`/api/v1/jobs/${jobId}/embedding`, { accessToken });
}

export async function createJobEmbedding(jobId: string, accessToken: string) {
  return apiRequest<EmbeddingStatus>(`/api/v1/jobs/${jobId}/embedding`, {
    method: "POST",
    accessToken,
  });
}

export type SkillMatchItem = {
  skill_id: string;
  skill: string;
  evidence_type: string;
  candidate_skill_id: string | null;
  candidate_evidence: string | null;
  hops: number | null;
};

export type MatchExplanation = {
  type: string;
  required_skill?: string;
  preferred_skill?: string;
  candidate_evidence?: string;
  canonical_skill_id?: string;
  ontology_version?: string;
  cosine?: number;
  [key: string]: unknown;
};

export type MatchResult = {
  candidate_id: string;
  job_id: string;
  current_match: number;
  potential: null;
  semantic_similarity: number | null;
  semantic_similarity_available: boolean;
  scoring_mode: "baseline";
  model_version: null;
  feature_schema_version: string;
  ontology_version: string;
  required_skill_coverage: number;
  preferred_skill_coverage: number;
  matched_skills: SkillMatchItem[];
  partial_skills: SkillMatchItem[];
  related_skills: SkillMatchItem[];
  missing_skills: SkillMatchItem[];
  explanations: MatchExplanation[];
};

export type CandidateJobMatchSummary = {
  job_id: string;
  job_title: string;
  current_match: number;
  potential: null;
  required_skill_coverage: number;
  missing_skills: SkillMatchItem[];
  partial_skills: SkillMatchItem[];
  related_skills: SkillMatchItem[];
  scoring_mode: "baseline";
  model_version: null;
  semantic_similarity_available: boolean;
};

export type JobCandidateMatchSummary = {
  candidate_id: string;
  identifier: string;
  headline: string | null;
  current_match: number;
  potential: null;
  required_skill_coverage: number;
  missing_skills: SkillMatchItem[];
  scoring_mode: "baseline";
  model_version: null;
};

export async function listCandidateJobs(candidateId: string, accessToken: string) {
  return apiRequest<{ items: CandidateJobMatchSummary[]; scoring_mode: "baseline"; sort: string; potential: null }>(
    `/api/v1/candidates/${candidateId}/jobs`,
    { accessToken },
  );
}

export async function getCandidateJobMatch(candidateId: string, jobId: string, accessToken: string) {
  return apiRequest<MatchResult>(`/api/v1/candidates/${candidateId}/jobs/${jobId}/match`, { accessToken });
}

export async function listJobCandidates(jobId: string, accessToken: string) {
  return apiRequest<{
    job_id: string;
    items: JobCandidateMatchSummary[];
    scoring_mode: "baseline";
    sort: string;
    potential: null;
  }>(`/api/v1/jobs/${jobId}/candidates`, { accessToken });
}
