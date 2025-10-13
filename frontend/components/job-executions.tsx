"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/api";
import {
  JobExecutionListResponse,
  JobExecution,
  JobExecutionListResponseSchema,
  JobConfiguration,
} from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { AlertCircle, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface JobExecutionsProps {
  executions: JobExecutionListResponse | null;
  jobs: JobConfiguration[];
}

/**
 * Format duration in seconds to human-readable format
 */
function formatDuration(
  started: string,
  completed: string | null | undefined,
): string {
  if (!completed) return "N/A";
  const startTime = new Date(started).getTime();
  const endTime = new Date(completed).getTime();
  const seconds = (endTime - startTime) / 1000;

  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Format timestamp to local date/time
 */
function formatDateTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString();
}

export function JobExecutions({
  executions: initialExecutions,
  jobs,
}: JobExecutionsProps) {
  const [selectedExecution, setSelectedExecution] =
    useState<JobExecution | null>(null);
  const [displayCount, setDisplayCount] = useState(20);
  const PAGE_SIZE = 20;
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const previousExecutionCount = useRef(0);

  // Create job name mapping
  const jobNameMap = useMemo(() => {
    const map = new Map<number, string>();
    jobs.forEach((job) => map.set(job.id, job.name));
    return map;
  }, [jobs]);

  // Reset display count when initial data changes
  const executionKey = initialExecutions?.total ?? 0;
  useEffect(() => {
    // This runs when the initial data changes, resetting pagination
    previousExecutionCount.current = 0;
  }, [executionKey]);

  // Derive display count from the execution key to avoid setState in effect
  const [resetKey, setResetKey] = useState(executionKey);
  if (resetKey !== executionKey) {
    setDisplayCount(20);
    setResetKey(executionKey);
  }

  // Fetch executions with pagination
  const {
    data: response,
    isLoading,
    isFetching,
  } = useQuery({
    queryKey: ["job-executions-infinite", displayCount],
    queryFn: async () => {
      const page = Math.ceil(displayCount / PAGE_SIZE);
      const result = await validatedGet(
        JobExecutionListResponseSchema,
        "/jobs/executions/all",
        {
          page: page,
          size: displayCount,
        },
      );
      return result;
    },
    enabled: !!initialExecutions,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchOnReconnect: false,
    placeholderData: (previousData) => previousData,
    staleTime: 15000,
  });

  const data = response?.success ? response.data : initialExecutions;
  const allExecutions = useMemo(
    () => data?.executions || [],
    [data?.executions],
  );
  const totalExecutions = data?.total || 0;
  const hasMore = allExecutions.length < totalExecutions;

  // Preserve scroll position when new executions load
  useEffect(() => {
    if (
      allExecutions.length > previousExecutionCount.current &&
      previousExecutionCount.current > 0
    ) {
      previousExecutionCount.current = allExecutions.length;
    } else if (allExecutions.length > 0) {
      previousExecutionCount.current = allExecutions.length;
    }
  }, [allExecutions.length]);

  // Load more function
  const loadMore = useCallback(() => {
    if (!isFetching && hasMore) {
      setDisplayCount((prev) => prev + PAGE_SIZE);
    }
  }, [isFetching, hasMore]);

  // Infinite scroll using Intersection Observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (first.isIntersecting) {
          loadMore();
        }
      },
      { threshold: 0.1, rootMargin: "100px" },
    );

    const currentRef = loadMoreRef.current;
    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
    };
  }, [loadMore]);

  // Get job name by ID
  const getJobName = (jobConfigId: number): string => {
    return jobNameMap.get(jobConfigId) || `Job #${jobConfigId}`;
  };

  if (isLoading || allExecutions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Executions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
            <FileText className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No job executions found
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Recent Executions</span>
            <Badge variant="secondary">{totalExecutions} total</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started At</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Stats</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {allExecutions.map((execution) => (
                  <TableRow
                    key={execution.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => setSelectedExecution(execution)}
                  >
                    <TableCell className="font-medium">
                      {getJobName(execution.job_config_id)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          execution.status === "success"
                            ? "default"
                            : execution.status === "failed"
                              ? "destructive"
                              : execution.status === "running"
                                ? "secondary"
                                : "outline"
                        }
                      >
                        {execution.status.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDateTime(execution.started_at)}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatDuration(
                        execution.started_at,
                        execution.completed_at,
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      <div className="flex flex-col gap-0.5">
                        <span>API: {execution.api_requests_made}</span>
                        <span className="text-xs text-muted-foreground">
                          Created: {execution.records_created} | Updated:{" "}
                          {execution.records_updated}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedExecution(execution);
                        }}
                      >
                        Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Infinite scroll trigger */}
          {hasMore && (
            <div ref={loadMoreRef} className="mt-4 flex justify-center py-4">
              {isFetching ? (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading more executions...</span>
                </div>
              ) : (
                <div className="text-sm text-muted-foreground">
                  Showing {allExecutions.length} of {totalExecutions} executions
                </div>
              )}
            </div>
          )}
          {!hasMore && allExecutions.length > 0 && (
            <div className="mt-4 flex justify-center py-4">
              <div className="text-sm text-muted-foreground">
                All {totalExecutions} executions loaded
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Execution Details Dialog */}
      <Dialog
        open={!!selectedExecution}
        onOpenChange={(open) => !open && setSelectedExecution(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Execution Details</DialogTitle>
            <DialogDescription>
              Detailed information for execution #{selectedExecution?.id}
            </DialogDescription>
          </DialogHeader>

          {selectedExecution && (
            <div className="space-y-4">
              {/* Status */}
              <div className="flex items-center justify-between">
                <span className="font-medium">Status</span>
                <Badge
                  variant={
                    selectedExecution.status === "success"
                      ? "default"
                      : selectedExecution.status === "failed"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {selectedExecution.status.toUpperCase()}
                </Badge>
              </div>

              {/* Timing */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium">Started At</p>
                  <p className="text-sm text-muted-foreground">
                    {formatDateTime(selectedExecution.started_at)}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Completed At</p>
                  <p className="text-sm text-muted-foreground">
                    {selectedExecution.completed_at
                      ? formatDateTime(selectedExecution.completed_at)
                      : "N/A"}
                  </p>
                </div>
              </div>

              {/* Statistics */}
              <div className="rounded-lg border p-4">
                <p className="mb-2 font-medium">Statistics</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">API Requests:</span>{" "}
                    <span className="font-medium">
                      {selectedExecution.api_requests_made}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      Records Created:
                    </span>{" "}
                    <span className="font-medium">
                      {selectedExecution.records_created}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">
                      Records Updated:
                    </span>{" "}
                    <span className="font-medium">
                      {selectedExecution.records_updated}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Duration:</span>{" "}
                    <span className="font-medium">
                      {formatDuration(
                        selectedExecution.started_at,
                        selectedExecution.completed_at,
                      )}
                    </span>
                  </div>
                </div>
              </div>

              {/* Error Message */}
              {selectedExecution.error_message && (
                <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
                  <div className="mb-2 flex items-center gap-2 font-medium text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    Error Message
                  </div>
                  <p className="text-sm">{selectedExecution.error_message}</p>
                </div>
              )}

              {/* Execution Log */}
              {selectedExecution.execution_log && (
                <div className="rounded-lg border bg-muted/50 p-4">
                  <p className="mb-2 font-medium">Execution Log</p>
                  <pre className="max-h-[200px] overflow-auto text-xs">
                    {JSON.stringify(selectedExecution.execution_log, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
