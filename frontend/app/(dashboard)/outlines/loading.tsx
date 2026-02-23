export default function OutlinesLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="space-y-2">
          <div className="h-7 w-32 rounded-xl bg-surface-tertiary" />
          <div className="h-4 w-52 rounded-xl bg-surface-tertiary" />
        </div>
        <div className="h-9 w-36 rounded-xl bg-surface-tertiary" />
      </div>

      {/* Table skeleton */}
      <div className="card overflow-hidden">
        {/* Table header */}
        <div className="px-5 py-3 border-b border-surface-tertiary flex gap-4">
          <div className="h-4 w-1/3 rounded-lg bg-surface-tertiary" />
          <div className="h-4 w-20 rounded-lg bg-surface-tertiary" />
          <div className="h-4 w-20 rounded-lg bg-surface-tertiary" />
          <div className="h-4 w-16 rounded-lg bg-surface-tertiary ml-auto" />
        </div>

        {/* Table rows */}
        <div className="divide-y divide-surface-tertiary">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="px-5 py-4 flex items-center gap-4">
              {/* Title + keyword */}
              <div className="flex-1 space-y-1.5">
                <div className="h-4 w-3/4 rounded-lg bg-surface-tertiary" />
                <div className="h-3 w-1/2 rounded-lg bg-surface-tertiary" />
              </div>
              {/* Status badge */}
              <div className="h-6 w-20 rounded-full bg-surface-tertiary flex-shrink-0" />
              {/* Sections count */}
              <div className="h-4 w-12 rounded-lg bg-surface-tertiary flex-shrink-0" />
              {/* Date */}
              <div className="h-4 w-20 rounded-lg bg-surface-tertiary flex-shrink-0" />
              {/* Menu */}
              <div className="h-8 w-8 rounded-lg bg-surface-tertiary flex-shrink-0" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
