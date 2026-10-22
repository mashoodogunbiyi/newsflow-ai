import { BrandMark } from "@/components/brand-mark";
import { ProductPreview } from "@/components/product-preview";
import { WorkflowStep } from "@/components/workflow-step";

const workflowSteps = [
  {
    number: "01",
    eyebrow: "Discover",
    title: "Start with an authorised source",
    description:
      "Browse permitted news records and choose one story with its source link, publication date, category, and rights metadata intact.",
  },
  {
    number: "02",
    eyebrow: "Ground",
    title: "Build a bounded fact pack",
    description:
      "NewsFlow AI separates usable source facts from instructions, rejects thin records, and keeps every generated claim traceable.",
  },
  {
    number: "03",
    eyebrow: "Create",
    title: "Generate text and visual direction",
    description:
      "Create a professional LinkedIn draft and an original conceptual illustration without copying source photography or branding.",
  },
  {
    number: "04",
    eyebrow: "Review",
    title: "Keep the final decision human",
    description:
      "Review, edit, save, copy, and download approved work. NewsFlow AI will not publish automatically on a user's behalf.",
  },
] as const;

const principles = [
  {
    label: "Source-grounded",
    detail: "Claims map back to an approved fact pack.",
  },
  {
    label: "Review-first",
    detail: "Nothing is published without a human decision.",
  },
  {
    label: "Rights-aware",
    detail: "Content permissions travel with each source record.",
  },
] as const;

export default function Home() {
  return (
    <main className="overflow-hidden">
      <section className="relative border-b border-emerald-950/10 bg-[#f7f6f2]">
        <div
          aria-hidden="true"
          className="absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-amber-400 to-transparent"
        />
        <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
          <BrandMark />
          <nav aria-label="Primary navigation" className="hidden items-center gap-8 md:flex">
            <a
              className="text-sm font-medium text-emerald-950/65 transition hover:text-emerald-950"
              href="#workflow"
            >
              Workflow
            </a>
            <a
              className="text-sm font-medium text-emerald-950/65 transition hover:text-emerald-950"
              href="#principles"
            >
              Guardrails
            </a>
            <a
              className="rounded-full border border-emerald-950/15 bg-white/60 px-4 py-2 text-sm font-semibold text-emerald-950 transition hover:border-emerald-950/30 hover:bg-white"
              href="#status"
            >
              Project status
            </a>
          </nav>
          <a
            className="rounded-full border border-emerald-950/15 bg-white/70 px-3.5 py-2 text-xs font-semibold text-emerald-950 md:hidden"
            href="#workflow"
          >
            Explore
          </a>
        </header>

        <div className="mx-auto grid w-full max-w-7xl gap-14 px-5 pb-20 pt-12 sm:px-8 sm:pb-24 sm:pt-16 lg:grid-cols-[0.88fr_1.12fr] lg:items-center lg:gap-18 lg:px-12 lg:pb-28 lg:pt-20">
          <div className="relative z-10 max-w-2xl">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-emerald-900/10 bg-white/75 px-3 py-1.5 text-xs font-semibold tracking-wide text-emerald-900 shadow-sm shadow-emerald-950/5">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              Engineering foundation · Fixture mode
            </div>
            <p className="mb-4 font-mono text-xs font-semibold uppercase tracking-[0.22em] text-emerald-800/70">
              From source facts to social story
            </p>
            <h1 className="max-w-3xl text-balance text-5xl font-semibold leading-[0.98] tracking-[-0.045em] text-emerald-950 sm:text-6xl lg:text-7xl">
              Turn careful reporting into confident LinkedIn content.
            </h1>
            <p className="mt-7 max-w-xl text-pretty text-lg leading-8 text-emerald-950/65 sm:text-xl">
              NewsFlow AI is a review-first workspace for transforming authorised news facts into
              professional drafts and original visual concepts, with the source and the human editor
              kept in view.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <a
                className="inline-flex min-h-12 items-center justify-center rounded-full bg-emerald-950 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/15 transition hover:-translate-y-0.5 hover:bg-emerald-900"
                href="#workflow"
              >
                Explore the workflow
                <span aria-hidden="true" className="ml-2">
                  ↓
                </span>
              </a>
              <a
                className="inline-flex min-h-12 items-center justify-center rounded-full border border-emerald-950/15 bg-white/60 px-6 py-3 text-sm font-semibold text-emerald-950 transition hover:border-emerald-950/30 hover:bg-white"
                href="#principles"
              >
                See the guardrails
              </a>
            </div>

            <dl className="mt-12 grid max-w-xl grid-cols-3 border-y border-emerald-950/10 py-5">
              <div>
                <dt className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-emerald-950/45">
                  Source
                </dt>
                <dd className="mt-1 text-sm font-semibold text-emerald-950 sm:text-base">
                  Authorised
                </dd>
              </div>
              <div className="border-l border-emerald-950/10 pl-4 sm:pl-6">
                <dt className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-emerald-950/45">
                  Claims
                </dt>
                <dd className="mt-1 text-sm font-semibold text-emerald-950 sm:text-base">
                  Fact-mapped
                </dd>
              </div>
              <div className="border-l border-emerald-950/10 pl-4 sm:pl-6">
                <dt className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-emerald-950/45">
                  Publishing
                </dt>
                <dd className="mt-1 text-sm font-semibold text-emerald-950 sm:text-base">Manual</dd>
              </div>
            </dl>
          </div>

          <ProductPreview />
        </div>
      </section>

      <section id="principles" className="bg-emerald-950 text-white">
        <div className="mx-auto grid w-full max-w-7xl gap-10 px-5 py-16 sm:px-8 sm:py-20 lg:grid-cols-[0.8fr_1.2fr] lg:items-end lg:px-12">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.22em] text-amber-300">
              Built around editorial control
            </p>
            <h2 className="mt-4 max-w-lg text-3xl font-semibold tracking-[-0.035em] text-balance sm:text-4xl">
              Generation is only useful when the evidence stays visible.
            </h2>
          </div>
          <div className="grid gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-3">
            {principles.map((principle) => (
              <div className="bg-emerald-950 p-5 sm:p-6" key={principle.label}>
                <div className="mb-8 h-1.5 w-8 rounded-full bg-amber-300" />
                <h3 className="font-semibold">{principle.label}</h3>
                <p className="mt-2 text-sm leading-6 text-white/60">{principle.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="workflow" className="bg-white">
        <div className="mx-auto w-full max-w-7xl px-5 py-20 sm:px-8 sm:py-24 lg:px-12 lg:py-28">
          <div className="grid gap-8 border-b border-emerald-950/10 pb-12 md:grid-cols-[0.9fr_1.1fr] md:items-end">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.22em] text-emerald-800/65">
                The intended experience
              </p>
              <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-emerald-950 sm:text-5xl">
                One story. Four deliberate steps.
              </h2>
            </div>
            <p className="max-w-xl text-lg leading-8 text-emerald-950/60 md:justify-self-end">
              The product is designed to reduce context switching while preserving the checks that
              responsible news-based content needs.
            </p>
          </div>

          <div className="grid gap-x-10 md:grid-cols-2">
            {workflowSteps.map((step) => (
              <WorkflowStep key={step.number} {...step} />
            ))}
          </div>
        </div>
      </section>

      <section id="status" className="border-y border-emerald-950/10 bg-[#eeeade]">
        <div className="mx-auto grid w-full max-w-7xl gap-10 px-5 py-20 sm:px-8 lg:grid-cols-[0.82fr_1.18fr] lg:px-12 lg:py-24">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-[0.22em] text-emerald-800/65">
              Current project state
            </p>
            <h2 className="mt-4 max-w-md text-4xl font-semibold tracking-[-0.04em] text-emerald-950">
              The foundation is live. The data gate stays closed.
            </h2>
            <p className="mt-5 max-w-lg leading-7 text-emerald-950/60">
              This interface uses no live CNN content. Development continues with original synthetic
              fixtures until an authorised source and its exact licence terms are approved.
            </p>
          </div>

          <div className="grid overflow-hidden rounded-3xl border border-emerald-950/10 bg-white shadow-xl shadow-emerald-950/5 sm:grid-cols-2">
            <div className="p-7 sm:p-8">
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800/60">
                Available now
              </p>
              <ul className="mt-6 space-y-4 text-sm text-emerald-950/75">
                <li className="flex gap-3">
                  <span aria-hidden="true" className="text-emerald-700">
                    ✓
                  </span>
                  Responsive frontend foundation
                </li>
                <li className="flex gap-3">
                  <span aria-hidden="true" className="text-emerald-700">
                    ✓
                  </span>
                  Fixture-first source contract
                </li>
                <li className="flex gap-3">
                  <span aria-hidden="true" className="text-emerald-700">
                    ✓
                  </span>
                  Approved governance guardrails
                </li>
              </ul>
            </div>
            <div className="border-t border-emerald-950/10 bg-emerald-950 p-7 text-white sm:border-l sm:border-t-0 sm:p-8">
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-amber-300">
                Coming next
              </p>
              <ul className="mt-6 space-y-4 text-sm text-white/70">
                <li>Authentication and user workspace</li>
                <li>Article dashboard and generation controls</li>
                <li>Review, save, copy, and export tools</li>
                <li>Live sources only after formal approval</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-[#f7f6f2]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 py-8 text-sm text-emerald-950/55 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12">
          <BrandMark />
          <p>Built with a fixture-first, review-first approach.</p>
        </div>
      </footer>
    </main>
  );
}
