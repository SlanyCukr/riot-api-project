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
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Execution Details</DialogTitle>
            <DialogDescription>
              Detailed information for execution #{selectedExecution?.id}
            </DialogDescription>
          </DialogHeader>

          {selectedExecution && (
            <div className="space-y-4 pb-4">
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
                  <pre className="max-h-[180px] overflow-auto rounded-md border bg-background p-3 text-xs">
                    {JSON.stringify(selectedExecution.execution_log, null, 2)}
                  </pre>
                </div>
              )}

              {/* Detailed Logs */}
              {selectedExecution.detailed_logs && (
                <div className="space-y-4">
                  {/* Log Summary */}
                  {selectedExecution.detailed_logs.summary && (
                    <div className="rounded-lg border bg-muted/50 p-4">
                      <p className="mb-3 font-medium">Log Summary</p>
                      <div className="grid grid-cols-4 gap-3 text-sm">
                        <div className="rounded border bg-background p-2">
                          <div className="text-xs text-muted-foreground">
                            Total Logs
                          </div>
                          <div className="text-lg font-semibold">
                            {selectedExecution.detailed_logs.summary.total_logs}
                          </div>
                        </div>
                        {selectedExecution.detailed_logs.summary.by_level && (
                          <>
                            {Object.entries(
                              selectedExecution.detailed_logs.summary.by_level,
                            ).map(([level, count]) => (
                              <div
                                key={level}
                                className={`rounded border p-2 ${
                                  level === "ERROR"
                                    ? "border-destructive/50 bg-destructive/5"
                                    : level === "WARNING"
                                      ? "border-yellow-500/50 bg-yellow-500/5"
                                      : "bg-background"
                                }`}
                              >
                                <div className="text-xs text-muted-foreground">
                                  {level}
                                </div>
                                <div className="text-lg font-semibold">
                                  {count as number}
                                </div>
                              </div>
                            ))}
                          </>
                        )}
                      </div>

                      {/* Errors */}
                      {selectedExecution.detailed_logs.summary.errors &&
                        selectedExecution.detailed_logs.summary.errors.length >
                          0 && (
                          <div className="mt-4">
                            <p className="mb-2 flex items-center gap-2 text-sm font-medium text-destructive">
                              <AlertCircle className="h-4 w-4" />
                              Errors (
                              {
                                selectedExecution.detailed_logs.summary.errors
                                  .length
                              }
                              )
                            </p>
                            <div className="max-h-[250px] space-y-2 overflow-auto rounded border border-destructive/20 bg-destructive/5 p-3">
                              {selectedExecution.detailed_logs.summary.errors.map(
                                (
                                  error: {
                                    message: string;
                                    timestamp: string;
                                    context?: Record<string, unknown>;
                                  },
                                  idx: number,
                                ) => {
                                  // Try to parse message if it's JSON
                                  let displayMessage = error.message;
                                  let parsedContext = error.context;

                                  try {
                                    if (
                                      typeof error.message === "string" &&
                                      error.message.startsWith("{")
                                    ) {
                                      const parsed = JSON.parse(error.message);
                                      displayMessage =
                                        parsed.event ||
                                        parsed.message ||
                                        error.message;
                                      parsedContext = {
                                        ...parsedContext,
                                        ...parsed,
                                      };
                                    }
                                  } catch {
                                    // Keep original message if parsing fails
                                  }

                                  return (
                                    <div
                                      key={idx}
                                      className="rounded border border-destructive/30 bg-background p-3 text-xs"
                                    >
                                      <div className="mb-1 font-medium text-destructive">
                                        {displayMessage}
                                      </div>
                                      {parsedContext && (
                                        <div className="mt-2 space-y-1 text-muted-foreground">
                                          {Object.entries(parsedContext)
                                            .filter(
                                              ([key]) =>
                                                ![
                                                  "event",
                                                  "message",
                                                  "timestamp",
                                                  "logger",
                                                  "level",
                                                ].includes(key),
                                            )
                                            .slice(0, 3)
                                            .map(([key, value]) => (
                                              <div
                                                key={key}
                                                className="break-all"
                                              >
                                                <span className="font-mono text-[10px]">
                                                  {key}:
                                                </span>{" "}
                                                <span className="text-[10px]">
                                                  {String(value).substring(
                                                    0,
                                                    80,
                                                  )}
                                                  {String(value).length > 80 &&
                                                    "..."}
                                                </span>
                                              </div>
                                            ))}
                                        </div>
                                      )}
                                      <div className="mt-2 text-[10px] text-muted-foreground">
                                        {new Date(
                                          error.timestamp,
                                        ).toLocaleString()}
                                      </div>
                                    </div>
                                  );
                                },
                              )}
                            </div>
                          </div>
                        )}

                      {/* Warnings */}
                      {selectedExecution.detailed_logs.summary.warnings &&
                        selectedExecution.detailed_logs.summary.warnings
                          .length > 0 && (
                          <div className="mt-4">
                            <p className="mb-2 text-sm font-medium text-yellow-600">
                              Warnings (
                              {
                                selectedExecution.detailed_logs.summary.warnings
                                  .length
                              }
                              )
                            </p>
                            <div className="max-h-[150px] space-y-2 overflow-auto rounded border border-yellow-500/20 bg-yellow-500/5 p-3">
                              {selectedExecution.detailed_logs.summary.warnings.map(
                                (
                                  warning: {
                                    message: string;
                                    timestamp: string;
                                  },
                                  idx: number,
                                ) => (
                                  <div
                                    key={idx}
                                    className="rounded border border-yellow-500/30 bg-background p-2 text-xs"
                                  >
                                    <div className="mb-1 font-medium text-yellow-700 dark:text-yellow-600">
                                      {warning.message}
                                    </div>
                                    <div className="text-[10px] text-muted-foreground">
                                      {new Date(
                                        warning.timestamp,
                                      ).toLocaleString()}
                                    </div>
                                  </div>
                                ),
                              )}
                            </div>
                          </div>
                        )}
                    </div>
                  )}

                  {/* Full Logs */}
                  {selectedExecution.detailed_logs.logs && (
                    <div className="rounded-lg border bg-muted/50 p-4">
                      <div className="mb-3 flex items-center justify-between">
                        <p className="font-medium">Detailed Logs</p>
                        <Badge variant="secondary">
                          {selectedExecution.detailed_logs.logs.length} entries
                        </Badge>
                      </div>
                      <div className="max-h-[300px] overflow-auto rounded-md border bg-background p-3">
                        <div className="space-y-2 font-mono text-[11px]">
                          {selectedExecution.detailed_logs.logs.map(
                            (log: Record<string, unknown>, idx: number) => {
                              const logLevel = typeof log.log_level === 'string'
                                ? log.log_level.toUpperCase()
                                : "INFO";

                              // Extract extra fields (everything except the standard fields)
                              const standardFields = new Set([
                                "log_level",
                                "timestamp",
                                "event",
                              ]);
                              const extraFields = Object.entries(log).filter(
                                ([key]) => !standardFields.has(key),
                              );

                              return (
                                <div
                                  key={idx}
                                  className={`rounded border-l-4 border-y border-r bg-muted/20 p-2 space-y-1.5 ${
                                    logLevel === "ERROR"
                                      ? "border-l-destructive"
                                      : logLevel === "WARNING"
                                        ? "border-l-yellow-500"
                                        : logLevel === "INFO"
                                          ? "border-l-blue-500"
                                          : logLevel === "DEBUG"
                                            ? "border-l-orange-500"
                                            : "border-l-muted"
                                  }`}
                                >
                                  {/* Main log line */}
                                  <div className="flex gap-2">
                                    <span
                                      className={`shrink-0 font-bold ${
                                        logLevel === "ERROR"
                                          ? "text-destructive"
                                          : logLevel === "WARNING"
                                            ? "text-yellow-600"
                                            : logLevel === "INFO"
                                              ? "text-blue-600"
                                              : logLevel === "DEBUG"
                                                ? "text-orange-600"
                                                : "text-muted-foreground"
                                      }`}
                                    >
                                      {logLevel.padEnd(7, " ")}
                                    </span>
                                    <span className="shrink-0 text-muted-foreground">
                                      {String(log.timestamp || "")}
                                    </span>
                                    <span className="flex-1 break-all">
                                      {String(log.event || "")}
                                    </span>
                                  </div>

                                  {/* Extra fields */}
                                  {extraFields.length > 0 && (
                                    <div className="space-y-0.5 text-[10px] text-muted-foreground/80 bg-background/50 rounded p-2 border border-muted">
                                      {extraFields.map(([key, value]) => (
                                        <div key={key} className="flex gap-2">
                                          <span className="font-mono font-semibold shrink-0">
                                            {key}:
                                          </span>
                                          <span className="break-all">
                                            {typeof value === "object"
                                              ? JSON.stringify(value)
                                              : String(value)}
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            },
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
