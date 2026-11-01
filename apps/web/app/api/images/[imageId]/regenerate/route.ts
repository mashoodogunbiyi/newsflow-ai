import { proxyImageGenerationRequest } from "@/lib/image-generation-proxy";

type ImageRegenerationRouteContext = {
  params: Promise<{ imageId: string }>;
};

export async function POST(request: Request, context: ImageRegenerationRouteContext) {
  const { imageId } = await context.params;
  return proxyImageGenerationRequest(request, imageId);
}
