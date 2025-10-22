"use client";

import { JobStatusResponse } from "@/lib/core/schemas";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Activity,
  Loader2,
  AlertTriangle,
} from "lucide-react";

interface SystemStatusProps {
  status: JobStatusResponse | null;
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

export function SystemStatus({ status }: SystemStatusProps) {
  if (!status) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <p className="text-sm text-muted-foreground">
              No status information available
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isHealthy = status.scheduler_running && status.running_executions === 0;
  const hasRunningJobs = status.running_executions > 0;
  const lastExecutionFailed = status.last_execution?.status === "FAILED";

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Scheduler Status */}
      <Card
        className={
          status.scheduler_running
            ? "border-green-500/50 bg-green-500/10"
            : "border-red-500/50 bg-red-500/10"
        }
      >
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Scheduler
              </p>
              <p className="mt-1 text-2xl font-bold">
                {status.scheduler_running ? "Running" : "Stopped"}
              </p>
            </div>
            {status.scheduler_running ? (
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            ) : (
              <XCircle className="h-8 w-8 text-red-500" />
            )}
          </div>
          <Badge
            variant={status.scheduler_running ? "default" : "destructive"}
            className="mt-2"
          >
            {status.scheduler_running ? "Healthy" : "Offline"}
          </Badge>
        </CardContent>
      </Card>

      {/* Active Jobs */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Active Jobs
              </p>
              <p className="mt-1 text-2xl font-bold">{status.active_jobs}</p>
            </div>
            <Activity className="h-8 w-8 text-blue-500" />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Enabled job configurations
          </p>
        </CardContent>
      </Card>

      {/* Running Executions */}
      <Card
        className={
          hasRunningJobs
            ? "border-yellow-500/50 bg-yellow-500/10"
            : "border-green-500/50 bg-green-500/10"
        }
      >
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Running Now
              </p>
              <p className="mt-1 text-2xl font-bold">
                {status.running_executions}
              </p>
            </div>
            {hasRunningJobs ? (
              <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
            ) : (
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            )}
          </div>
          <Badge
            variant={hasRunningJobs ? "secondary" : "outline"}
            className="mt-2"
          >
            {hasRunningJobs ? "In Progress" : "Idle"}
          </Badge>
        </CardContent>
      </Card>

      {/* Last Execution */}
      <Card
        className={
          lastExecutionFailed
            ? "border-red-500/50 bg-red-500/10"
            : "border-green-500/50 bg-green-500/10"
        }
      >
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">
                Last Execution
              </p>
              {status.last_execution ? (
                <>
                  <p className="mt-1 text-sm font-semibold">
                    {formatRelativeTime(status.last_execution.started_at)}
                  </p>
                  <Badge
                    variant={
                      status.last_execution.status === "SUCCESS"
                        ? "default"
                        : status.last_execution.status === "FAILED"
                          ? "destructive"
                          : "secondary"
                    }
                    className="mt-2"
                  >
                    {status.last_execution.status}
                  </Badge>
                </>
              ) : (
                <p className="mt-1 text-sm text-muted-foreground">None</p>
              )}
            </div>
            {lastExecutionFailed ? (
              <AlertTriangle className="h-8 w-8 text-red-500" />
            ) : (
              <Clock className="h-8 w-8 text-green-500" />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Health Summary - Full Width */}
      <Card className="md:col-span-2 lg:col-span-4">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-muted-foreground">
                System Health
              </p>
              <p className="mt-1 text-xl font-bold">
                {isHealthy
                  ? "All Systems Operational"
                  : hasRunningJobs
                    ? "Jobs in Progress"
                    : !status.scheduler_running
                      ? "Scheduler Offline"
                      : "Check Required"}
              </p>
            </div>
            <div className="flex items-center gap-6">
              {status.scheduler_running && (
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Scheduler</p>
                  <CheckCircle2 className="mx-auto mt-1 h-6 w-6 text-green-500" />
                </div>
              )}
              {status.active_jobs > 0 && (
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Active Jobs</p>
                  <p className="mt-1 text-lg font-bold">{status.active_jobs}</p>
                </div>
              )}
              {hasRunningJobs && (
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Running</p>
                  <Loader2 className="mx-auto mt-1 h-6 w-6 animate-spin text-yellow-500" />
                </div>
              )}
              {lastExecutionFailed && (
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Last Failed</p>
                  <AlertTriangle className="mx-auto mt-1 h-6 w-6 text-red-500" />
                </div>
              )}
            </div>
          </div>

          {/* Next Run Time */}
          {status.next_run_time && (
            <div className="mt-4 border-t pt-4">
              <p className="text-sm text-muted-foreground">
                Next scheduled run:{" "}
                <span className="font-medium text-foreground">
                  {formatRelativeTime(status.next_run_time)}
                </span>
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
