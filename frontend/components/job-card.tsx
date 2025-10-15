"use client";

import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { validatedPost, validatedGet, validatedPut } from "@/lib/api";
import {
  JobConfiguration,
  JobTriggerResponseSchema,
  JobExecutionListResponseSchema,
  JobConfigurationSchema,
} from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

import { Label } from "@/components/ui/label";
import {
  Play,
  History,
  Clock,
  CalendarClock,
  ChevronDown,
  ChevronUp,
  Loader2,
  Settings,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import cronstrue from "cronstrue";

interface JobCardProps {
  job: JobConfiguration;
}

/**
 * Convert cron expression to human-readable format
 */
function formatCronSchedule(schedule: string): string {
  try {
    // Check if it's a cron expression (starts with 5-7 parts)
    const parts = schedule.trim().split(/\s+/);
    if (parts.length >= 5 && parts.length <= 7) {
      return cronstrue.toString(schedule, { use24HourTimeFormat: true });
    }
    // Otherwise return as-is (might be interval format)
    return schedule;
  } catch {
    return schedule;
  }
}

/**
 * Format duration in seconds to human-readable format
 */
function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return "N/A";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Format timestamp to relative time
 */
function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function JobCard({ job }: JobCardProps) {
  const [showHistory, setShowHistory] = useState(false);
  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [configJson, setConfigJson] = useState(
    JSON.stringify(job.config_json || {}, null, 2),
  );
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch latest execution for this job
  const { data: executionsResult } = useQuery({
    queryKey: ["job-executions", job.id],
    queryFn: () =>
      validatedGet(
        JobExecutionListResponseSchema,
        `/jobs/${job.id}/executions`,
        {
          page: 1,
          size: 1,
        },
      ),
    enabled: !!job.id,
  });

  const lastExecution =
    executionsResult?.success && executionsResult.data.executions.length > 0
      ? executionsResult.data.executions[0]
      : null;

  // Calculate duration
  const duration =
    lastExecution?.started_at && lastExecution?.completed_at
      ? (new Date(lastExecution.completed_at).getTime() -
          new Date(lastExecution.started_at).getTime()) /
        1000
      : null;

  // Trigger job mutation
  const triggerMutation = useMutation({
    mutationFn: () =>
      validatedPost(JobTriggerResponseSchema, `/jobs/${job.id}/trigger`),
    onSuccess: (result) => {
      if (result.success) {
        toast({
          title: "Job Triggered",
          description: result.data.message,
        });
        // Invalidate queries to refresh data
        queryClient.invalidateQueries({ queryKey: ["jobs"] });
        queryClient.invalidateQueries({ queryKey: ["job-executions"] });
        queryClient.invalidateQueries({ queryKey: ["job-status"] });
      } else {
        toast({
          title: "Failed to Trigger Job",
          description: result.error.message,
          variant: "error",
        });
      }
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to trigger job",
        variant: "error",
      });
    },
  });

  // Update job config mutation
  const updateConfigMutation = useMutation({
    mutationFn: (config: Record<string, unknown>) =>
      validatedPut(JobConfigurationSchema, `/jobs/${job.id}`, {
        config_json: config,
      }),
    onSuccess: (result) => {
      if (result.success) {
        toast({
          title: "Configuration Updated",
          description: "Job configuration has been updated successfully",
        });
        setShowConfigDialog(false);
        // Invalidate queries to refresh data
        queryClient.invalidateQueries({ queryKey: ["jobs"] });
      } else {
        toast({
          title: "Failed to Update Configuration",
          description: result.error.message,
          variant: "error",
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error?.message || "Failed to update configuration",
        variant: "error",
      });
    },
  });

  const handleTrigger = () => {
    triggerMutation.mutate();
  };

  const toggleHistory = () => {
    setShowHistory(!showHistory);
  };

  const handleUpdateConfig = () => {
    try {
      const parsed = JSON.parse(configJson);
      updateConfigMutation.mutate(parsed);
    } catch {
      toast({
        title: "Invalid JSON",
        description: "Please check your configuration JSON syntax",
        variant: "error",
      });
    }
  };

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader>
        <CardTitle className="flex items-start justify-between gap-2">
          <div className="flex-1">
            <div className="mb-1 flex items-center gap-2">
              <span className="text-lg">{job.name}</span>
              <Badge variant={job.is_active ? "default" : "secondary"}>
                {job.is_active ? "Active" : "Disabled"}
              </Badge>
            </div>
            <div className="text-sm font-normal text-muted-foreground">
              {job.job_type.replace(/_/g, " ")}
            </div>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Schedule */}
        <div className="flex items-start gap-2 text-sm">
          <CalendarClock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <div className="flex-1">
            <p className="font-medium">Schedule</p>
            <p className="text-muted-foreground">
              {formatCronSchedule(job.schedule)}
            </p>
          </div>
        </div>

        {/* Last Execution */}
        {lastExecution && (
          <div className="flex items-start gap-2 text-sm">
            <Clock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
            <div className="flex-1">
              <p className="font-medium">Last Execution</p>
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    lastExecution.status === "success"
                      ? "default"
                      : lastExecution.status === "failed"
                        ? "destructive"
                        : "secondary"
                  }
                  className="text-xs"
                >
                  {lastExecution.status.toUpperCase()}
                </Badge>
                <span className="text-muted-foreground">
                  {formatRelativeTime(lastExecution.started_at)}
                </span>
                {duration && (
                  <span className="text-muted-foreground">
                    • {formatDuration(duration)}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Configuration Section */}
        {job.config_json && Object.keys(job.config_json).length > 0 && (
          <div className="rounded-md border p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium">Configuration</p>
              <Dialog open={showConfigDialog} onOpenChange={setShowConfigDialog}>
                <DialogTrigger asChild>
                  <Button size="sm" variant="ghost" className="h-7 px-2">
                    <Settings className="h-3.5 w-3.5" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Edit Job Configuration</DialogTitle>
                    <DialogDescription>
                      Update the JSON configuration for {job.name}. Changes
                      take effect on the next job run.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="config-json">Configuration JSON</Label>
                      <textarea
                        id="config-json"
                        value={configJson}
                        onChange={(e) => setConfigJson(e.target.value)}
                        className="min-h-[300px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        placeholder='{\n  "key": "value"\n}'
                      />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setShowConfigDialog(false)}
                      disabled={updateConfigMutation.isPending}
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleUpdateConfig}
                      disabled={updateConfigMutation.isPending}
                    >
                      {updateConfigMutation.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Save Changes"
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            <div className="space-y-1">
              {Object.entries(job.config_json).map(([key, value]) => (
                <div key={key} className="flex items-baseline gap-2 text-xs">
                  <span className="font-medium text-muted-foreground">
                    {key}:
                  </span>
                  <span className="font-mono">
                    {typeof value === "object"
                      ? JSON.stringify(value)
                      : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={handleTrigger}
            disabled={!job.is_active || triggerMutation.isPending}
            className="flex-1"
          >
            {triggerMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Triggering...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Trigger Now
              </>
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={toggleHistory}
            className="flex-1"
          >
            <History className="mr-2 h-4 w-4" />
            History
            {showHistory ? (
              <ChevronUp className="ml-1 h-4 w-4" />
            ) : (
              <ChevronDown className="ml-1 h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Execution History (Expandable) */}
        {showHistory && (
          <div className="mt-4 border-t pt-4">
            <p className="mb-2 text-sm font-medium">Recent Executions</p>
            {/* TODO: Add execution history list here */}
            <p className="text-xs text-muted-foreground">
              View full execution history in the Executions tab
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
