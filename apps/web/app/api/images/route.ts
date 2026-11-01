import { proxyImageGenerationRequest } from "@/lib/image-generation-proxy";

export async function POST(request: Request) {
  return proxyImageGenerationRequest(request);
}
