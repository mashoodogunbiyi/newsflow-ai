import Link from "next/link";

export function BrandMark() {
  return (
    <Link className="group inline-flex items-center gap-3" href="/" aria-label="NewsFlow AI home">
      <span className="relative grid h-9 w-9 place-items-center overflow-hidden rounded-xl bg-emerald-950 shadow-sm">
        <span className="absolute -right-2 -top-2 h-6 w-6 rounded-full bg-amber-300" />
        <span className="relative h-3.5 w-3.5 rotate-45 rounded-[0.2rem] border-2 border-white" />
      </span>
      <span className="text-base font-semibold tracking-[-0.025em] text-emerald-950">
        NewsFlow <span className="text-emerald-700">AI</span>
      </span>
    </Link>
  );
}
