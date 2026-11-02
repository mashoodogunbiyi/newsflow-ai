import { proxyDraftDeletion } from "@/lib/draft-deletion-proxy";

type DraftRouteContext = {
  params: Promise<{ draftId: string }>;
};

export async function DELETE(request: Request, context: DraftRouteContext) {
  const { draftId } = await context.params;
  return proxyDraftDeletion(request, draftId);
}
