import { proxyDraftCreation } from "@/lib/draft-persistence-proxy";

export async function POST(request: Request) {
  return proxyDraftCreation(request);
}
