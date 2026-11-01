type LoadingStateProps = {
  message?: string;
};

export function LoadingState({ message = "Loading your workspace..." }: LoadingStateProps) {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      className="grid min-h-[24rem] place-items-center rounded-3xl border border-emerald-950/10 bg-white px-6"
    >
      <div className="text-center text-emerald-950">
        <span
          aria-hidden="true"
          className="mx-auto block h-9 w-9 animate-spin rounded-full border-2 border-emerald-900/20 border-t-emerald-900 motion-reduce:animate-none"
        />
        <p className="mt-4 text-sm font-semibold">{message}</p>
      </div>
    </div>
  );
}
