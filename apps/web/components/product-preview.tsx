export function ProductPreview() {
  return (
    <div className="relative mx-auto w-full max-w-2xl lg:mx-0">
      <div
        aria-hidden="true"
        className="absolute -inset-6 -z-10 rounded-[2.5rem] bg-[radial-gradient(circle_at_top_right,rgba(244,191,88,0.38),transparent_48%),radial-gradient(circle_at_bottom_left,rgba(20,101,76,0.18),transparent_46%)] blur-2xl"
      />
      <div className="overflow-hidden rounded-[1.75rem] border border-emerald-950/15 bg-[#102f26] p-2 shadow-2xl shadow-emerald-950/20 sm:rounded-[2rem] sm:p-3">
        <div className="overflow-hidden rounded-[1.3rem] bg-[#fbfaf7] sm:rounded-[1.45rem]">
          <div className="flex items-center justify-between border-b border-emerald-950/10 px-4 py-3 sm:px-5">
            <div className="flex items-center gap-1.5" aria-hidden="true">
              <span className="h-2.5 w-2.5 rounded-full bg-[#ff8c72]" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
            </div>
            <div className="flex items-center gap-2 rounded-full bg-emerald-50 px-2.5 py-1 text-[0.62rem] font-semibold uppercase tracking-[0.14em] text-emerald-800">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Fixture mode
            </div>
          </div>

          <div className="grid min-h-[29rem] lg:grid-cols-[0.82fr_1.18fr]">
            <div className="border-b border-emerald-950/10 p-5 sm:p-6 lg:border-b-0 lg:border-r">
              <div className="flex items-center justify-between">
                <p className="font-mono text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-emerald-800/55">
                  Source record
                </p>
                <span className="rounded-full border border-amber-500/30 bg-amber-50 px-2 py-1 text-[0.58rem] font-bold uppercase tracking-[0.12em] text-amber-800">
                  Synthetic
                </span>
              </div>
              <h2 className="mt-6 text-2xl font-semibold leading-tight tracking-[-0.03em] text-emerald-950">
                A verified source becomes a focused professional story.
              </h2>
              <p className="mt-4 text-sm leading-6 text-emerald-950/55">
                A bounded fixture demonstrates how title, date, category, source URL,
                and permitted facts stay attached throughout generation.
              </p>
              <div className="mt-7 space-y-3 border-t border-emerald-950/10 pt-5">
                {[
                  ["Category", "Technology"],
                  ["Fact pack", "6 mapped facts"],
                  ["Attribution", "Required"],
                ].map(([label, value]) => (
                  <div className="flex items-center justify-between gap-4" key={label}>
                    <span className="text-xs text-emerald-950/45">{label}</span>
                    <span className="text-xs font-semibold text-emerald-950">{value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col p-5 sm:p-6">
              <div className="flex items-center justify-between gap-4">
                <p className="font-mono text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-emerald-800/55">
                  Draft workspace
                </p>
                <span className="text-[0.62rem] font-semibold text-emerald-700">Review required</span>
              </div>

              <div className="mt-5 rounded-2xl border border-emerald-950/10 bg-white p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <span className="grid h-8 w-8 place-items-center rounded-full bg-emerald-950 text-[0.65rem] font-bold text-white">
                    NF
                  </span>
                  <div>
                    <p className="text-xs font-semibold text-emerald-950">NewsFlow draft</p>
                    <p className="text-[0.62rem] text-emerald-950/40">Professional · concise</p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-emerald-950/70">
                  A strong post does not need more facts. It needs the right facts,
                  a clear point of view, and a final human check before it leaves the
                  workspace.
                </p>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {["#ResponsibleAI", "#ContentWorkflow", "#NewsTech"].map((tag) => (
                    <span className="text-[0.65rem] font-medium text-emerald-700" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-3 grid grid-cols-[0.9fr_1.1fr] gap-3">
                <div className="relative min-h-28 overflow-hidden rounded-2xl bg-emerald-950 p-3">
                  <span className="absolute -right-5 -top-5 h-20 w-20 rounded-full border-[14px] border-amber-300/90" />
                  <span className="absolute bottom-3 left-3 h-10 w-10 rotate-45 rounded-lg border border-white/40" />
                  <p className="absolute bottom-3 right-3 text-[0.55rem] font-semibold uppercase tracking-[0.12em] text-white/60">
                    AI concept
                  </p>
                </div>
                <div className="flex flex-col justify-between rounded-2xl border border-emerald-950/10 bg-[#eeeade] p-3.5">
                  <p className="text-[0.62rem] font-semibold uppercase tracking-[0.12em] text-emerald-800/55">
                    Claim check
                  </p>
                  <div>
                    <p className="text-xl font-semibold tracking-[-0.03em] text-emerald-950">6 / 6</p>
                    <p className="text-[0.65rem] text-emerald-950/45">facts mapped</p>
                  </div>
                </div>
              </div>

              <div className="mt-auto flex items-center justify-between pt-5">
                <span
                  className="rounded-full border border-emerald-950/10 px-3 py-2 text-[0.65rem] font-semibold text-emerald-950/55"
                >
                  Edit draft
                </span>
                <span
                  className="rounded-full bg-emerald-950 px-3 py-2 text-[0.65rem] font-semibold text-white"
                >
                  Review output
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
