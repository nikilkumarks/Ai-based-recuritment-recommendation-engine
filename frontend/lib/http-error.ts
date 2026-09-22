import { ApiError } from "@/lib/api";

export function describeHttpError(error: unknown, fallback = "Something went wrong."): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    if (error.status === 403) {
      return "You do not have permission to view this page.";
    }
    if (error.status === 404) {
      return "This resource was not found.";
    }
    if (error.status === 409) {
      return error.message || "This request conflicts with the current state.";
    }
    if (error.status === 413) {
      return "The file is too large to upload.";
    }
    if (error.status === 415) {
      return "That file type is not supported.";
    }
    if (error.status === 422) {
      return error.message || "Please check the form and try again.";
    }
    if (error.status >= 500) {
      return "The server could not complete this request. Try again later.";
    }
    return error.message || fallback;
  }
  if (error instanceof TypeError) {
    return "Network error. Check your connection and try again.";
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}
