import { CopyPostButton } from "@/components/export/copy-post-button";
import { DownloadImageButton } from "@/components/export/download-image-button";

type ContentExportActionsProps = {
  imageId: string | null;
  text: string;
};

export function ContentExportActions({ imageId, text }: ContentExportActionsProps) {
  return (
    <section
      aria-labelledby="content-export-heading"
      className="mt-6 rounded-3xl border border-emerald-950/10 bg-emerald-50/50 p-5 sm:p-6"
    >
      <p className="font-mono text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
        Manual export
      </p>
      <h3 className="mt-2 text-lg font-semibold text-emerald-950" id="content-export-heading">
        Copy or download your reviewed content.
      </h3>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-emerald-950/70">
        Review the draft against its visible source before export. Copying and downloading do not
        publish to LinkedIn or connect to a LinkedIn account.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <CopyPostButton text={text} />
        <DownloadImageButton imageId={imageId} />
      </div>
      <p className="mt-4 border-t border-emerald-950/10 pt-4 text-xs leading-5 text-emerald-950/70">
        Selected illustrations are AI-generated and require human review before external use. News
        source attribution remains visible in the preview and must be preserved where required.
      </p>
    </section>
  );
}
