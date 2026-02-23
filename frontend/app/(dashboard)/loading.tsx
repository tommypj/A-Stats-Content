export default function DashboardLoading() {
  return (
    <div className="space-y-8 animate-pulse">
      {/* Header */}
      <div className="space-y-2">
        <div className="h-7 w-56 rounded-xl bg-surface-tertiary" />
        <div className="h-4 w-72 rounded-xl bg-surface-tertiary" />
      </div>

      {/* Stat cards — 4 columns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="h-10 w-10 rounded-xl bg-surface-tertiary" />
              <div className="h-4 w-16 rounded-lg bg-surface-tertiary" />
            </div>
            <div className="space-y-2">
              <div className="h-7 w-20 rounded-lg bg-surface-tertiary" />
              <div className="h-4 w-28 rounded-lg bg-surface-tertiary" />
            </div>
          </div>
        ))}
      </div>

      {/* Content blocks — 2 side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <div key={i} className="card p-5 space-y-4">
            <div className="h-5 w-36 rounded-lg bg-surface-tertiary" />
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-surface-tertiary flex-shrink-0" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-4 w-3/4 rounded-lg bg-surface-tertiary" />
                    <div className="h-3 w-1/2 rounded-lg bg-surface-tertiary" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
