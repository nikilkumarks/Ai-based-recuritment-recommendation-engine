const HINT_COOKIE = "session_hint";

export function setSessionHint(role: string): void {
  document.cookie = `${HINT_COOKIE}=${encodeURIComponent(role)}; Path=/; SameSite=Lax`;
}

export function clearSessionHint(): void {
  document.cookie = `${HINT_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function readSessionHint(): string | null {
  if (typeof document === "undefined") {
    return null;
  }
  const parts = document.cookie.split(";").map((part) => part.trim());
  const match = parts.find((part) => part.startsWith(`${HINT_COOKIE}=`));
  if (!match) {
    return null;
  }
  return decodeURIComponent(match.slice(HINT_COOKIE.length + 1)) || null;
}
