export default function ImagesLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="space-y-2">
          <div className="h-7 w-40 rounded-xl bg-surface-tertiary" />
          <div className="h-4 w-56 rounded-xl bg-surface-tertiary" />
        </div>
        <div className="h-9 w-36 rounded-xl bg-surface-tertiary" />
      </div>

      {/* Image grid skeleton */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <div key={i} className="card overflow-hidden space-y-0">
            {/* Image placeholder — square aspect ratio */}
            <div className="aspect-square bg-surface-tertiary" />
            {/* Card footer */}
            <div className="p-3 space-y-1.5">
              <div className="h-3.5 w-4/5 rounded-lg bg-surface-tertiary" />
              <div className="h-3 w-1/2 rounded-lg bg-surface-tertiary" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
