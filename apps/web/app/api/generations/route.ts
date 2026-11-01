import { proxyGenerationRequest } from "@/lib/generation-proxy";

export async function POST(request: Request) {
  return proxyGenerationRequest(request);
}
