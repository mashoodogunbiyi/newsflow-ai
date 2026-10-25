export default function DashboardLoading() {
  return (
    <main
      aria-busy="true"
      aria-live="polite"
      className="grid min-h-screen place-items-center bg-[#f7f6f2] px-5"
    >
      <div className="text-center text-emerald-950">
        <span
          aria-hidden="true"
          className="mx-auto block h-9 w-9 animate-spin rounded-full border-2 border-emerald-900/20 border-t-emerald-900"
        />
        <p className="mt-4 text-sm font-semibold">Confirming your secure session...</p>
      </div>
    </main>
  );
}
