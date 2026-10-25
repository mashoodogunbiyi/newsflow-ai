export function shouldOptimisticallyRedirectFromDashboard(
  pathname: string,
  hasSessionCookie: boolean,
) {
  return pathname.startsWith("/dashboard") && !hasSessionCookie;
}
