export type AuthenticatedUser = {
  id: string;
  email: string;
};

export type AuthenticationState =
  | { status: "authenticated"; user: AuthenticatedUser }
  | { status: "unauthenticated" }
  | { status: "unavailable" };

export type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
  };
};

export function isAuthenticatedUser(value: unknown): value is AuthenticatedUser {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return typeof candidate.id === "string" && typeof candidate.email === "string";
}
