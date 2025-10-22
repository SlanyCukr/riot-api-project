"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { validatedGet } from "@/lib/core/api";
import {
  JobConfigurationSchema,
  JobConfiguration,
  JobExecutionListResponseSchema,
  JobStatusResponseSchema,
} from "@/lib/core/schemas";
import { JobCard, JobExecutions, SystemStatus } from "@/features/jobs";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Loader2, AlertCircle, Clock } from "lucide-react";
import { z } from "zod";

const REFRESH_INTERVAL = 15000; // 15 seconds

export default function JobsPage() {
  const [secondsUntilRefresh, setSecondsUntilRefresh] = useState(15);

  // Fetch all job configurations
  const {
    data: jobsResult,
    isLoading: isLoadingJobs,
    error: jobsError,
    dataUpdatedAt: jobsUpdatedAt,
  } = useQuery({
    queryKey: ["jobs"],
    queryFn: () =>
      validatedGet(z.array(JobConfigurationSchema), "/jobs/", {
        active_only: false,
      }),
    refetchInterval: REFRESH_INTERVAL,
  });

  // Fetch all recent executions
  const {
    data: executionsResult,
    isLoading: isLoadingExecutions,
    dataUpdatedAt: executionsUpdatedAt,
  } = useQuery({
    queryKey: ["job-executions-all"],
    queryFn: () =>
      validatedGet(JobExecutionListResponseSchema, "/jobs/executions/all", {
        page: 1,
        size: 20,
      }),
    refetchInterval: REFRESH_INTERVAL,
  });

  // Fetch system status
  const {
    data: statusResult,
    isLoading: isLoadingStatus,
    dataUpdatedAt: statusUpdatedAt,
  } = useQuery({
    queryKey: ["job-status"],
    queryFn: () =>
      validatedGet(JobStatusResponseSchema, "/jobs/status/overview"),
    refetchInterval: REFRESH_INTERVAL,
  });

  // Countdown timer for next refresh
  useEffect(() => {
    const lastUpdate = Math.max(
      jobsUpdatedAt,
      executionsUpdatedAt,
      statusUpdatedAt,
    );
    if (lastUpdate === 0) return;

    const interval = setInterval(() => {
      const elapsed = Date.now() - lastUpdate;
      const remaining = Math.max(
        0,
        Math.ceil((REFRESH_INTERVAL - elapsed) / 1000),
      );
      setSecondsUntilRefresh(remaining);
    }, 100);

    return () => clearInterval(interval);
  }, [jobsUpdatedAt, executionsUpdatedAt, statusUpdatedAt]);

  const jobs = jobsResult?.success ? jobsResult.data : [];
  const executions = executionsResult?.success ? executionsResult.data : null;
  const status = statusResult?.success ? statusResult.data : null;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <Card
        id="header-card"
        className="mb-6 bg-[#152b56] p-6 text-white dark:bg-[#0a1428]"
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Background Jobs</h1>
            <div className="mt-2 flex items-center gap-2 text-sm text-white/70">
              <Clock className="h-4 w-4" />
              <span>Auto-refresh in {secondsUntilRefresh}s</span>
            </div>
          </div>
          <ThemeToggle />
        </div>
        <p className="text-sm leading-relaxed">
          Monitor and manage automated background jobs for player tracking and
          data processing
        </p>
      </Card>

      {/* System Status Dashboard */}
      <div className="mb-6">
        {isLoadingStatus ? (
          <Card className="p-8">
            <div className="flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          </Card>
        ) : (
          <SystemStatus status={status} />
        )}
      </div>

      {/* Tabs for Jobs and Executions */}
      <Tabs defaultValue="jobs" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="jobs">Job Configurations</TabsTrigger>
          <TabsTrigger value="executions">Recent Executions</TabsTrigger>
        </TabsList>

        {/* Job Configurations Tab */}
        <TabsContent value="jobs" className="mt-6">
          {isLoadingJobs ? (
            <Card className="p-8">
              <div className="flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            </Card>
          ) : jobsError || !jobsResult?.success ? (
            <Card className="p-8">
              <div className="flex flex-col items-center justify-center gap-2">
                <AlertCircle className="h-8 w-8 text-destructive" />
                <p className="text-sm text-muted-foreground">
                  Failed to load job configurations
                </p>
              </div>
            </Card>
          ) : jobs.length === 0 ? (
            <Card className="p-8">
              <p className="text-center text-muted-foreground">
                No job configurations found
              </p>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {jobs.map((job: JobConfiguration) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          )}
        </TabsContent>

        {/* Recent Executions Tab */}
        <TabsContent value="executions" className="mt-6">
          {isLoadingExecutions ? (
            <Card className="p-8">
              <div className="flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            </Card>
          ) : (
            <JobExecutions executions={executions} jobs={jobs} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
