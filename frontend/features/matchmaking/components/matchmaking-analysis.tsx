"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  PlayCircle,
  StopCircle,
  Clock,
  AlertCircle,
  CheckCircle,
  Loader2,
  Scale,
} from "lucide-react";

import {
  startMatchmakingAnalysis,
  getLatestMatchmakingAnalysis,
  cancelMatchmakingAnalysis,
  getMatchmakingAnalysisStatus,
} from "@/lib/core/api";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";

interface MatchmakingAnalysisProps {
  puuid: string;
}

export function MatchmakingAnalysis({ puuid }: MatchmakingAnalysisProps) {
  const queryClient = useQueryClient();
  // Track if we're starting a new analysis to prevent showing old state
  const [isStartingNewAnalysis, setIsStartingNewAnalysis] = useState(false);

  // Query for the latest analysis
  const {
    data: latestAnalysis,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["matchmaking-analysis", puuid],
    queryFn: async () => {
      const result = await getLatestMatchmakingAnalysis(puuid);
      if (!result.success) {
        if (result.error.status === 404) {
          return null;
        }
        // Don't throw for 404, just return null
        console.warn("Failed to fetch analysis:", result.error.message);
        return null;
      }
      return result.data;
    },
    retry: false,
    staleTime: 1000, // Consider data stale after 1 second
  });

  // Determine if we should poll based on analysis status
  const isAnalysisActive =
    latestAnalysis?.status === "pending" ||
    latestAnalysis?.status === "in_progress";

  // Poll for status updates when analysis is in progress
  const { data: statusUpdate } = useQuery({
    queryKey: ["matchmaking-analysis-status", latestAnalysis?.id],
    queryFn: async () => {
      if (!latestAnalysis?.id) return null;
      const result = await getMatchmakingAnalysisStatus(latestAnalysis.id);
      if (!result.success) {
        return null;
      }
      return result.data;
    },
    enabled: isAnalysisActive && !!latestAnalysis?.id,
    refetchInterval: 3000, // Poll every 3 seconds
    staleTime: 0, // Always consider data stale to ensure fresh status
  });

  // Handle completed status - refetch to get final results
  const prevStatusRef = useRef<string | null>(null);
  useEffect(() => {
    const currentStatus = statusUpdate?.status || latestAnalysis?.status;
    if (
      currentStatus === "completed" &&
      prevStatusRef.current !== "completed"
    ) {
      prevStatusRef.current = "completed";
      // Use setTimeout to avoid synchronous setState in effect
      setTimeout(() => {
        refetch();
        // Also invalidate the matchmaking analysis results component
        queryClient.invalidateQueries({
          queryKey: ["matchmaking-analysis-results", puuid],
        });
      }, 0);
    } else if (currentStatus) {
      prevStatusRef.current = currentStatus;
    }
  }, [
    statusUpdate?.status,
    latestAnalysis?.status,
    refetch,
    queryClient,
    puuid,
  ]);

  // Reset isStartingNewAnalysis when we detect the new analysis has loaded
  useEffect(() => {
    if (isStartingNewAnalysis && latestAnalysis) {
      // Check if the latest analysis is actually new (pending or in_progress)
      if (
        latestAnalysis.status === "pending" ||
        latestAnalysis.status === "in_progress"
      ) {
        // Use setTimeout to avoid synchronous setState in effect
        setTimeout(() => {
          setIsStartingNewAnalysis(false);
        }, 0);
      }
    }
  }, [isStartingNewAnalysis, latestAnalysis]); // Start analysis mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      const result = await startMatchmakingAnalysis(puuid);
      if (!result.success) {
        throw new Error(result.error.message);
      }
      return result.data;
    },
    onMutate: async () => {
      // Mark that we're starting a new analysis to prevent showing old state
      setIsStartingNewAnalysis(true);
    },
    onSuccess: (data) => {
      toast.success("Matchmaking analysis started");
      // Immediately update the query data to show the new analysis
      // This prevents flashing through old cancelled/completed states
      queryClient.setQueryData(["matchmaking-analysis", puuid], data);
      // Also clear the status query to prevent showing old "processing" state
      queryClient.setQueryData(["matchmaking-analysis-status", data.id], null);
      // Invalidate both queries to ensure we get fresh data
      queryClient.invalidateQueries({
        queryKey: ["matchmaking-analysis", puuid],
      });
      queryClient.invalidateQueries({
        queryKey: ["matchmaking-analysis-status", data.id],
      });
      // Clear the flag after new data is set
      setIsStartingNewAnalysis(false);
    },
    onError: (error: Error) => {
      toast.error(`Failed to start analysis: ${error.message}`);
      setIsStartingNewAnalysis(false);
    },
  });

  // Cancel analysis mutation
  const cancelMutation = useMutation({
    mutationFn: async () => {
      if (!latestAnalysis?.id) {
        throw new Error("No analysis to cancel");
      }
      const result = await cancelMatchmakingAnalysis(latestAnalysis.id);
      if (!result.success) {
        throw new Error(result.error.message);
      }
      return result.data;
    },
    onSuccess: () => {
      toast.success("Analysis cancelled");
      // Invalidate both the main analysis and status queries
      queryClient.invalidateQueries({
        queryKey: ["matchmaking-analysis", puuid],
      });
      queryClient.invalidateQueries({
        queryKey: ["matchmaking-analysis-status", latestAnalysis?.id],
      });
    },
    onError: (error: Error) => {
      toast.error(`Failed to cancel analysis: ${error.message}`);
    },
  });

  const handleStartAnalysis = () => {
    startMutation.mutate();
  };

  const handleCancelAnalysis = () => {
    cancelMutation.mutate();
  };

  // Use status update if available, otherwise use latest analysis
  // But ignore old analysis data if we're starting a new one
  const currentStatus = isStartingNewAnalysis
    ? null
    : statusUpdate || latestAnalysis;

  const isActive =
    isStartingNewAnalysis ||
    currentStatus?.status === "pending" ||
    currentStatus?.status === "in_progress";
  const isCompleted = currentStatus?.status === "completed";
  const isFailed = currentStatus?.status === "failed";
  const isCancelled = currentStatus?.status === "cancelled";

  const progressPercentage =
    currentStatus && currentStatus.total_requests > 0
      ? Math.round(
          (currentStatus.progress / currentStatus.total_requests) * 100,
        )
      : 0;

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            Matchmaking Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading analysis...</p>
        </CardContent>
      </Card>
    );
  }

  // Show start card when:
  // 1. Not currently starting a new analysis
  // 2. No active analysis (pending/in_progress)
  // This ensures the component is always visible when player is selected
  const shouldShowStartCard = !isStartingNewAnalysis && !isActive;

  if (shouldShowStartCard) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            Matchmaking Analysis
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Analyze matchmaking fairness for this player&apos;s last 10 ranked
            matches. This will calculate average winrates for teammates vs
            enemies.
          </p>
          <Button
            onClick={handleStartAnalysis}
            disabled={startMutation.isPending}
            className="w-full matchmaking-start-btn"
          >
            {isStartingNewAnalysis || startMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <PlayCircle className="mr-2 h-4 w-4" />
                {latestAnalysis ? "Run New Analysis" : "Start Analysis"}
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Scale className="h-5 w-5 text-primary" />
            Matchmaking Analysis
          </span>
          {isActive && (
            <div className="flex items-center gap-2 text-sm font-normal text-muted-foreground">
              <Clock className="h-4 w-4" />
              {currentStatus?.estimated_minutes_remaining &&
              currentStatus.estimated_minutes_remaining > 0
                ? `~${currentStatus.estimated_minutes_remaining} min remaining`
                : "Calculating time..."}
            </div>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Status Alert */}
        {isActive && (
          <Alert>
            <Loader2 className="h-4 w-4 animate-spin" />
            <AlertDescription>
              {currentStatus?.total_requests && currentStatus.total_requests > 0
                ? `Analysis in progress... Processing ${
                    currentStatus.progress || 0
                  } of ${currentStatus.total_requests} requests`
                : "Starting analysis..."}
            </AlertDescription>
          </Alert>
        )}

        {isFailed && !isStartingNewAnalysis && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {currentStatus?.error_message || "Analysis failed"}
            </AlertDescription>
          </Alert>
        )}

        {isCancelled && !isActive && !isStartingNewAnalysis && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Analysis was cancelled.{" "}
              {currentStatus?.progress && currentStatus.progress > 0
                ? `Processed ${currentStatus.progress} of ${
                    currentStatus.total_requests || 0
                  } requests before cancellation.`
                : ""}
            </AlertDescription>
          </Alert>
        )}

        {/* Progress Bar - only show for active analysis, not cancelled */}
        {isActive && (
          <div className="space-y-2">
            <Progress value={progressPercentage} className="h-2" />
            <p className="text-xs text-muted-foreground text-center">
              {progressPercentage}% complete
            </p>
          </div>
        )}

        {/* Results Table */}
        {isCompleted && currentStatus?.results && !isStartingNewAnalysis && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
              <CheckCircle className="h-4 w-4" />
              <span>Analysis completed successfully</span>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Team</TableHead>
                  <TableHead className="text-right">
                    Average Winrate (Last 10 Matches)
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium">Your Team</TableCell>
                  <TableCell className="text-right font-mono">
                    {(currentStatus.results.team_avg_winrate * 100).toFixed(1)}%
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium">Enemy Team</TableCell>
                  <TableCell className="text-right font-mono">
                    {(currentStatus.results.enemy_avg_winrate * 100).toFixed(1)}
                    %
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>

            <p className="text-xs text-muted-foreground">
              Based on {currentStatus.results.matches_analyzed} ranked matches
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          {isActive ? (
            <Button
              onClick={handleCancelAnalysis}
              disabled={cancelMutation.isPending}
              variant="destructive"
              className="w-full matchmaking-cancel-btn"
            >
              {cancelMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Cancelling...
                </>
              ) : (
                <>
                  <StopCircle className="mr-2 h-4 w-4" />
                  Cancel Analysis
                </>
              )}
            </Button>
          ) : (
            <Button
              onClick={handleStartAnalysis}
              disabled={isStartingNewAnalysis || startMutation.isPending}
              className="w-full matchmaking-start-btn"
            >
              {isStartingNewAnalysis || startMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <PlayCircle className="mr-2 h-4 w-4" />
                  {isCompleted || isFailed || isCancelled
                    ? "Run New Analysis"
                    : "Start Analysis"}
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
