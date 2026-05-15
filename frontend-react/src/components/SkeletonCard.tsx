interface Props {
  count?: number;
}

export default function SkeletonCard({ count = 3 }: Props) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-gray-900/60 rounded-2xl border border-gray-800/50 p-4 animate-pulse">
          <div className="flex items-center justify-between">
            <div className="space-y-2 flex-1">
              <div className="h-4 bg-gray-800 rounded-lg w-1/3" />
              <div className="h-3 bg-gray-800/50 rounded-lg w-2/3" />
            </div>
            <div className="flex gap-2 ml-4">
              <div className="h-8 w-10 bg-gray-800 rounded-xl" />
              <div className="h-8 w-10 bg-gray-800 rounded-xl" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
