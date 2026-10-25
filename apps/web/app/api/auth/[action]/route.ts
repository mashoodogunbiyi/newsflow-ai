import { proxyAuthenticationRequest } from "@/lib/auth-proxy";

type AuthenticationRouteContext = {
  params: Promise<{ action: string }>;
};

async function handle(request: Request, context: AuthenticationRouteContext) {
  const { action } = await context.params;
  return proxyAuthenticationRequest(request, action);
}

export async function GET(request: Request, context: AuthenticationRouteContext) {
  return handle(request, context);
}

export async function POST(request: Request, context: AuthenticationRouteContext) {
  return handle(request, context);
}
