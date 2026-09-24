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
    end_date: string | null;
    is_current: boolean;
    evidence?: { value?: string; evidence?: string }[];
  }[];
  education: {
    institution: string | null;
    degree: string | null;
    field_of_study: string | null;
    start_date: string | null;
    end_date: string | null;
    evidence?: { value?: string; evidence?: string }[];
  }[];
  projects: {
    name: string | null;
    description: string | null;
    url: string | null;
    technologies?: SkillMention[];
    evidence?: { value?: string; evidence?: string }[];
  }[];
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
  employment_type: string | null;
  seniority: string | null;
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

export async function createJob(
  accessToken: string,
  payload: {
    title: string;
    description_raw: string;
    location?: string;
    employment_type?: string;
  },
) {
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

export type PotentialStatus = "available" | "not_applicable";

export type ScoringMode = "baseline" | "trained";

export type MatchExplanation = {
  type?: string;
  kind?: string;
  method?: string;
  title?: string;
  note?: string;
  required_skill?: string;
  preferred_skill?: string;
  candidate_evidence?: string;
  canonical_skill_id?: string;
  ontology_version?: string;
  cosine?: number;
  features?: { feature: string; contribution?: number | null; importance?: number | null }[];
  [key: string]: unknown;
};

export type SuggestedSkillPath = {
  target_skill: string;
  target_skill_id: string;
  distance: number;
  relation: string | null;
  label: string;
  steps: { skill: string; skill_id: string }[];
};

export type MatchResult = {
  candidate_id: string;
  job_id: string;
  current_match: number;
  potential: number | null;
  potential_status: PotentialStatus;
  potential_components: Record<string, number | null>;
  suggested_skill_paths: SuggestedSkillPath[];
  semantic_similarity: number | null;
  semantic_similarity_available: boolean;
  scoring_mode: ScoringMode;
  model_version: string | null;
  model_relevance_score: number | null;
  ml_explanations: MatchExplanation[];
  fallback_reason: string | null;
  feature_schema_version: string;
  ontology_version: string;
  required_skill_coverage: number;
  preferred_skill_coverage: number;
  matched_skills: SkillMatchItem[];
  partial_skills: SkillMatchItem[];
  related_skills: SkillMatchItem[];
  missing_skills: SkillMatchItem[];
  explanations: MatchExplanation[];
  components?: { name: string; value: number; weight: number; available: boolean }[];
  gaps?: { skill: string; skill_id: string; type: string }[];
};

export type CandidateJobMatchSummary = {
  job_id: string;
  job_title: string;
  current_match: number;
  potential: number | null;
  potential_status: PotentialStatus;
  required_skill_coverage: number;
  missing_skills: SkillMatchItem[];
  partial_skills: SkillMatchItem[];
  related_skills: SkillMatchItem[];
  scoring_mode: ScoringMode;
  model_version: string | null;
  model_relevance_score: number | null;
  semantic_similarity_available: boolean;
};

export type JobCandidateMatchSummary = {
  candidate_id: string;
  identifier: string;
  headline: string | null;
  current_match: number;
  potential: number | null;
  potential_status: PotentialStatus;
  required_skill_coverage: number;
  missing_skills: SkillMatchItem[];
  related_skills: SkillMatchItem[];
  scoring_mode: ScoringMode;
  model_version: string | null;
  model_relevance_score: number | null;
  current_decision: string | null;
  is_applicant?: boolean;
  application_status?: string | null;
};

export type RecruiterDecisionView = {
  id: string;
  recruiter_id: string;
  job_id: string;
  candidate_id: string;
  action: string;
  reason: string | null;
  note: string | null;
  match_run_id: string | null;
  feature_snapshot_id: string | null;
  created_at: string;
};

export type RecruiterOverview = {
  jobs: number;
  candidates: number;
  applications: number;
  shortlist_count: number;
  reject_count: number;
  review_count: number;
  decision_rate: number | null;
  shortlist_rate: number | null;
  disclaimer: string;
};

export type CountItem = { name: string; count: number };

export type RecruiterSkillsAnalytics = {
  required_demand: CountItem[];
  preferred_demand: CountItem[];
  candidate_supply: CountItem[];
  top_missing_skills: CountItem[];
  top_adjacent_skills: CountItem[];
  gaps: {
    skill: string;
    required_jobs: number;
    candidate_supply: number;
    missing_comparisons: number;
    related_comparisons: number;
  }[];
};

export type DistributionBucket = { bucket: string; count: number };

export type RecruiterMatchingAnalytics = {
  current_match: DistributionBucket[];
  potential: DistributionBucket[];
  required_skill_coverage: DistributionBucket[];
  semantic_similarity: DistributionBucket[];
};

export type DatasetSnapshotSummary = {
  id: string;
  name: string;
  created_at: string | null;
  row_count: number | null;
  positive_count: number;
  negative_count: number;
  excluded_count: number;
  label_policy_version: string | null;
  feature_schema_versions: string[];
  ontology_versions: string[];
  embedding_versions: string[];
  sufficient_for_training_experiment: boolean;
  trained: boolean;
};

export async function createRecruiterDecision(
  jobId: string,
  candidateId: string,
  accessToken: string,
  body: { action: "shortlist" | "reject" | "review" | "hire"; reason?: string; note?: string },
) {
  return apiRequest<RecruiterDecisionView>(
    `/api/v1/jobs/${jobId}/candidates/${candidateId}/decisions`,
    { method: "POST", accessToken, json: body },
  );
}

export async function getRecruiterOverview(accessToken: string) {
  return apiRequest<RecruiterOverview>(`/api/v1/analytics/recruiter/overview`, { accessToken });
}

export async function getRecruiterSkills(accessToken: string) {
  return apiRequest<RecruiterSkillsAnalytics>(`/api/v1/analytics/recruiter/skills`, { accessToken });
}

export async function getRecruiterMatching(accessToken: string) {
  return apiRequest<RecruiterMatchingAnalytics>(`/api/v1/analytics/recruiter/matching`, { accessToken });
}

export async function listDatasetSnapshots(accessToken: string) {
  return apiRequest<DatasetSnapshotSummary[]>(`/api/v1/admin/datasets/snapshots`, { accessToken });
}

export async function createDatasetSnapshot(accessToken: string) {
  return apiRequest<DatasetSnapshotSummary>(`/api/v1/admin/datasets/snapshots`, {
    method: "POST",
    accessToken,
  });
}

export async function listCandidateJobs(candidateId: string, accessToken: string) {
  return apiRequest<{ items: CandidateJobMatchSummary[]; scoring_mode: ScoringMode; sort: string }>(
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
    scoring_mode: ScoringMode;
    sort: string;
  }>(`/api/v1/jobs/${jobId}/candidates`, { accessToken });
}

export type MlModelSummary = {
  id: string;
  version: string;
  algorithm: string;
  status: string;
  feature_schema_version: string;
  dataset_snapshot_id: string | null;
  created_at: string | null;
  activated_at: string | null;
  evaluation: Record<string, unknown> | null;
  baseline_comparison: Record<string, unknown>;
  activation: Record<string, unknown>;
  class_balance: Record<string, unknown> | null;
  leakage_checks: string[] | null;
  cv_folds: number | null;
  random_seed: number | null;
  test_fixture_only: boolean;
  warning: string | null;
  target_note: string;
};

export async function listMlModels(accessToken: string) {
  return apiRequest<MlModelSummary[]>(`/api/v1/admin/models`, { accessToken });
}

export async function activateMlModel(modelId: string, accessToken: string) {
  return apiRequest<MlModelSummary>(`/api/v1/admin/models/${modelId}/activate`, {
    method: "POST",
    accessToken,
  });
}

export async function rejectMlModel(modelId: string, accessToken: string) {
  return apiRequest<MlModelSummary>(`/api/v1/admin/models/${modelId}/reject`, {
    method: "POST",
    accessToken,
  });
}

export type FunnelAnalytics = {
  jobs: number;
  applications: number;
  reviewed: number;
  shortlisted: number;
  rejected: number;
};

export async function getRecruiterFunnel(accessToken: string) {
  return apiRequest<FunnelAnalytics>(`/api/v1/analytics/recruiter/funnel`, { accessToken });
}

export async function getAdminOverview(accessToken: string) {
  return apiRequest<RecruiterOverview>(`/api/v1/analytics/admin/overview`, { accessToken });
}

export async function getAdminSkills(accessToken: string) {
  return apiRequest<RecruiterSkillsAnalytics>(`/api/v1/analytics/admin/skills`, { accessToken });
}

export type CareerPathList = {
  candidate_id: string;
  job_id: string | null;
  label: string;
  disclaimer: string;
  items: SuggestedSkillPath[];
};

export async function getCareerPaths(
  candidateId: string,
  accessToken: string,
  jobId?: string,
) {
  const query = jobId ? `?job_id=${jobId}` : "";
  return apiRequest<CareerPathList>(`/api/v1/candidates/${candidateId}/career-paths${query}`, {
    accessToken,
  });
}

export type CounterfactualResult = {
  candidate_id: string;
  job_id: string;
  skill_id: string;
  skill_name: string;
  baseline_current_match: number;
  simulated_current_match: number;
  delta: number;
  potential_before: number | null;
  potential_after: number | null;
  potential_delta: number | null;
  persisted: boolean;
};

export async function simulateAddSkill(
  candidateId: string,
  jobId: string,
  skillId: string,
  accessToken: string,
) {
  return apiRequest<CounterfactualResult>(
    `/api/v1/candidates/${candidateId}/jobs/${jobId}/counterfactual`,
    { method: "POST", accessToken, json: { skill_id: skillId } },
  );
}

export type RecruiterDecisionList = {
  job_id: string;
  candidate_id: string;
  current_action: string | null;
  items: RecruiterDecisionView[];
  label_note: string;
};

export async function listRecruiterDecisions(
  jobId: string,
  candidateId: string,
  accessToken: string,
) {
  return apiRequest<RecruiterDecisionList>(
    `/api/v1/jobs/${jobId}/candidates/${candidateId}/decisions`,
    { accessToken },
  );
}

export type OntologySkill = {
  id: string;
  canonical_name: string;
  slug: string;
  description: string | null;
  category: string | null;
  status: string;
};

export async function listOntologySkills(accessToken: string) {
  return apiRequest<{ ontology_version: string | null; items: OntologySkill[] }>(
    `/api/v1/admin/ontology/skills`,
    { accessToken },
  );
}

export async function listOntologyVersions(accessToken: string) {
  return apiRequest<{ id: string; version: string; checksum: string; status: string }[]>(
    `/api/v1/admin/ontology/versions`,
    { accessToken },
  );
}

export async function getOntologyValidation(accessToken: string) {
  return apiRequest<{ ok: boolean; errors: string[] }>(`/api/v1/admin/ontology/validation`, {
    accessToken,
  });
}

export async function seedOntology(accessToken: string) {
  return apiRequest<{ id: string; version: string; checksum: string; status: string }>(
    `/api/v1/admin/ontology/seed`,
    {
      method: "POST",
      accessToken,
    },
  );
}

export async function createOntologySkill(
  accessToken: string,
  payload: { canonical_name: string; category?: string; description?: string },
) {
  return apiRequest<{ ontology_version: string | null; items: OntologySkill[] }>(
    `/api/v1/admin/ontology/skills`,
    { method: "POST", accessToken, json: payload },
  );
}

export async function createOntologyAlias(
  accessToken: string,
  payload: { skill_id: string; alias: string },
) {
  return apiRequest<{ id: string; alias: string }>(`/api/v1/admin/ontology/aliases`, {
    method: "POST",
    accessToken,
    json: payload,
  });
}

export async function createOntologyRelation(
  accessToken: string,
  payload: {
    source_skill_id: string;
    target_skill_id: string;
    relation: "parent_of" | "related_to" | "similar_to";
  },
) {
  return apiRequest<{ id: string; relation: string }>(`/api/v1/admin/ontology/relations`, {
    method: "POST",
    accessToken,
    json: payload,
  });
}

export type ApplicationView = {
  id: string;
  candidate_id: string;
  job_id: string;
  status: string;
  applied_at: string;
  job_title?: string | null;
  organization_name?: string | null;
};

export type CandidateDecisionView = {
  id: string;
  candidate_id: string;
  job_id: string;
  action: string;
  note?: string | null;
  created_at: string;
};

export type AdminUserView = {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
  last_login_at?: string | null;
  organization_id?: string | null;
  organization_name?: string | null;
  membership_role?: string | null;
};

export async function createApplication(candidateId: string, jobId: string, accessToken: string) {
  return apiRequest<ApplicationView>(`/api/v1/candidates/${candidateId}/applications`, {
    method: "POST",
    accessToken,
    json: { job_id: jobId },
  });
}

export async function listCandidateApplications(candidateId: string, accessToken: string) {
  return apiRequest<{ items: ApplicationView[]; total: number }>(
    `/api/v1/candidates/${candidateId}/applications`,
    { accessToken },
  );
}

export async function getCandidateApplication(candidateId: string, jobId: string, accessToken: string) {
  return apiRequest<ApplicationView | null>(
    `/api/v1/candidates/${candidateId}/jobs/${jobId}/application`,
    { accessToken },
  );
}

export async function createCandidateDecision(
  candidateId: string,
  jobId: string,
  action: "apply" | "save" | "dismiss",
  accessToken: string,
  note?: string,
) {
  return apiRequest<CandidateDecisionView>(
    `/api/v1/candidates/${candidateId}/jobs/${jobId}/decisions`,
    {
      method: "POST",
      accessToken,
      json: { action, note },
    },
  );
}

export async function listSavedJobs(candidateId: string, accessToken: string) {
  return apiRequest<{ items: JobSummary[] }>(`/api/v1/candidates/${candidateId}/saved-jobs`, {
    accessToken,
  });
}

export async function searchOntologySkills(query: string, accessToken: string) {
  return apiRequest<OntologySkill[]>(
    `/api/v1/ontology/search?q=${encodeURIComponent(query)}`,
    { accessToken },
  );
}

export async function addCandidateSkill(candidateId: string, skillIdentifier: string, accessToken: string) {
  return apiRequest<ProfileView>(`/api/v1/candidates/${candidateId}/profile/skills`, {
    method: "POST",
    accessToken,
    json: { skill: skillIdentifier, skill_identifier: skillIdentifier },
  });
}

export async function removeCandidateSkill(candidateId: string, skillIdentifier: string, accessToken: string) {
  return apiRequest<ProfileView>(
    `/api/v1/candidates/${candidateId}/profile/skills/${encodeURIComponent(skillIdentifier)}`,
    {
      method: "DELETE",
      accessToken,
    },
  );
}

export async function listAdminUsers(accessToken: string) {
  return apiRequest<{ items: AdminUserView[]; total: number }>(`/api/v1/admin/users`, {
    accessToken,
  });
}

