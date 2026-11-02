import { proxyImageDownloadRequest } from "@/lib/image-download-proxy";

type ImageDownloadRouteContext = {
  params: Promise<{ imageId: string }>;
};

export async function GET(request: Request, context: ImageDownloadRouteContext) {
  const { imageId } = await context.params;
  return proxyImageDownloadRequest(request, imageId);
}
