import { proxyImageContentRequest } from "@/lib/image-content-proxy";

type ImageContentRouteContext = {
  params: Promise<{ imageId: string }>;
};

export async function GET(request: Request, context: ImageContentRouteContext) {
  const { imageId } = await context.params;
  return proxyImageContentRequest(request, imageId);
}
