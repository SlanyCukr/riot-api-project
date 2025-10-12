import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8 flex items-start justify-between">
          <div className="flex-1 text-center">
            <Skeleton className="mx-auto mb-2 h-12 w-96" />
            <Skeleton className="mx-auto h-6 w-[600px]" />
          </div>
          <Skeleton className="h-10 w-10 rounded-md" />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <Skeleton className="h-[400px] w-full rounded-lg" />
          </div>
          <div className="space-y-6 lg:col-span-2">
            <Skeleton className="h-[200px] w-full rounded-lg" />
            <Skeleton className="h-[400px] w-full rounded-lg" />
          </div>
        </div>
      </div>
    </div>
  );
}
