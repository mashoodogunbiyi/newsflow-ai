const PROTECTED_ROUTE_PREFIXES = ["/account", "/dashboard", "/generate", "/library"] as const;

export function isProtectedWorkspaceRoute(pathname: string) {
  return PROTECTED_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export function shouldOptimisticallyRedirectFromWorkspace(
  pathname: string,
  hasSessionCookie: boolean,
) {
  return isProtectedWorkspaceRoute(pathname) && !hasSessionCookie;
}
