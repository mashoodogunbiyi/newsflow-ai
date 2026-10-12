type WorkflowStepProps = {
  number: string;
  eyebrow: string;
  title: string;
  description: string;
};

export function WorkflowStep({
  number,
  eyebrow,
  title,
  description,
}: WorkflowStepProps) {
  return (
    <article className="grid grid-cols-[auto_1fr] gap-5 border-b border-emerald-950/10 py-9 sm:gap-7 sm:py-11">
      <span className="font-mono text-sm font-semibold text-amber-600">{number}</span>
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-800/55">
          {eyebrow}
        </p>
        <h3 className="mt-3 text-2xl font-semibold tracking-[-0.025em] text-emerald-950">
          {title}
        </h3>
        <p className="mt-3 max-w-xl leading-7 text-emerald-950/60">{description}</p>
      </div>
    </article>
  );
}
