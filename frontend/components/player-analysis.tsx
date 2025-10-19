"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  Clock,
  RefreshCw,
} from "lucide-react";

import {
  DetectionResponseSchema,
  DetectionExistsResponseSchema,
  type DetectionRequest,
} from "@/lib/schemas";
import { validatedPost, validatedGet } from "@/lib/api";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface PlayerAnalysisProps {
  puuid: string;
}

function formatTimeAgo(dateString: string): {
  text: string;
  isOld: boolean;
} {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  let text: string;
  if (diffMins < 1) {
    text = "just now";
  } else if (diffMins < 60) {
    text = `${diffMins} minute${diffMins !== 1 ? "s" : ""} ago`;
  } else if (diffHours < 24) {
    text = `${diffHours} hour${diffHours !== 1 ? "s" : ""} ago`;
  } else {
    text = `${diffDays} day${diffDays !== 1 ? "s" : ""} ago`;
  }

  const isOld = diffHours > 24;

  return { text, isOld };
}

export function PlayerAnalysis({ puuid }: PlayerAnalysisProps) {
  const queryClient = useQueryClient();

  const { data: latestDetection, isLoading: isLoadingLatest } = useQuery({
    queryKey: ["latest-detection", puuid],
    queryFn: async () => {
      const result = await validatedGet(
        DetectionResponseSchema,
        `/player-analysis/player/${puuid}/latest`
      );
      if (!result.success) {
        if (result.error.status === 404) {
          return null;
        }
        throw new Error(result.error.message);
      }
      return result.data;
    },
    retry: false,
  });

  const { data: existsCheck } = useQuery({
    queryKey: ["detection-exists", puuid],
    queryFn: async () => {
      const result = await validatedGet(
        DetectionExistsResponseSchema,
        `/player-analysis/player/${puuid}/exists`
      );
      if (!result.success) {
        return null;
      }
      return result.data;
    },
    retry: false,
  });

  // Simply show cached status when we have latestDetection
  const showingCached = !!latestDetection;

  const { mutate, isPending, error } = useMutation({
    mutationFn: async () => {
      const request: DetectionRequest = {
        puuid,
        min_games: 30,
        queue_filter: 420,
        force_reanalyze: true,
      };
      return validatedPost(
        DetectionResponseSchema,
        "/player-analysis/analyze",
        request
      );
    },
    onSuccess: () => {
      // Invalidate queries to refresh detection data
      queryClient.invalidateQueries({
        queryKey: ["latest-detection", puuid],
      });
      queryClient.invalidateQueries({
        queryKey: ["detection-exists", puuid],
      });
    },
  });

  const buttonText = () => {
    if (isPending) return "Analyzing...";
    if (existsCheck?.exists) return "Update Analysis";
    return "Run Analysis";
  };

  const timestampInfo =
    existsCheck?.exists && existsCheck.last_analysis
      ? formatTimeAgo(existsCheck.last_analysis)
      : null;

  const getConfidenceVariant = (
    confidence: string
  ): "default" | "secondary" | "destructive" => {
    switch (confidence) {
      case "high":
        return "destructive";
      case "medium":
        return "default";
      case "low":
        return "secondary";
      default:
        return "secondary";
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 0.8) return "text-red-600";
    if (score >= 0.6) return "text-yellow-600";
    if (score >= 0.4) return "text-blue-600";
    return "text-muted-foreground";
  };

  const isInitialLoading = isLoadingLatest && !latestDetection;
  const detection = latestDetection;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Player Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isInitialLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : !detection ? (
          <div className="space-y-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <p className="font-medium mb-2">
                  Player analysis requires at least 30 ranked matches
                </p>
                <p className="text-sm text-muted-foreground">
                  If this player was recently tracked, matches are still being
                  fetched in the background. Please check back in a few minutes.
                </p>
              </AlertDescription>
            </Alert>
            <div className="text-center py-4">
              <Button
                onClick={() => mutate()}
                disabled={isPending}
                type="submit"
                className="w-full"
              >
                {isPending ? (
                  <>
                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                    Analyzing...
                  </>
                ) : (
                  buttonText()
                )}
              </Button>
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error instanceof Error
                    ? error.message
                    : "Failed to run player analysis. Please try again."}
                </AlertDescription>
              </Alert>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {showingCached && timestampInfo && (
              <Alert
                className={cn(
                  "border-blue-200 bg-blue-50",
                  timestampInfo.isOld && "border-yellow-200 bg-yellow-50"
                )}
              >
                <Clock className="h-4 w-4" />
                <AlertDescription>
                  <div className="flex items-center justify-between">
                    <span>
                      Last analyzed: <strong>{timestampInfo.text}</strong>
                    </span>
                    {timestampInfo.isOld && (
                      <Badge variant="outline" className="ml-2">
                        ⚠️ May be outdated
                      </Badge>
                    )}
                  </div>
                </AlertDescription>
              </Alert>
            )}

            <div
              className={cn(
                "flex items-center justify-between rounded-lg border-2 p-4",
                detection.is_smurf
                  ? "border-red-500 bg-red-50"
                  : "border-green-500 bg-green-50"
              )}
            >
              <div className="flex items-center gap-3">
                {detection.is_smurf ? (
                  <AlertTriangle className="h-8 w-8 text-red-600" />
                ) : (
                  <CheckCircle className="h-8 w-8 text-green-600" />
                )}
                <div>
                  <h3 className="text-lg font-semibold">
                    {detection.is_smurf
                      ? "Smurf Detected"
                      : "No Smurf Indicators"}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {detection.reason}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div
                  className={cn(
                    "text-2xl font-bold",
                    getScoreColor(detection.detection_score)
                  )}
                >
                  {(detection.detection_score * 100).toFixed(0)}%
                </div>
                {detection.confidence_level !== "none" ? (
                  <Badge
                    variant={getConfidenceVariant(detection.confidence_level)}
                  >
                    {detection.confidence_level.toUpperCase()} confidence
                  </Badge>
                ) : (
                  <Badge variant="secondary">Not detected</Badge>
                )}
              </div>
            </div>

            <div>
              <h4 className="mb-3 font-medium">Detection Factors:</h4>
              <div className="space-y-2">
                {detection.factors.map((factor, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between rounded-md bg-muted p-3"
                  >
                    <div className="flex-1">
                      <div className="text-sm font-medium">
                        {factor.name
                          .replace(/_/g, " ")
                          .replace(/\b\w/g, (l) => l.toUpperCase())}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {factor.description}
                      </div>
                    </div>
                    <div className="text-right">
                      <div
                        className={cn(
                          "text-sm font-medium",
                          factor.meets_threshold
                            ? "text-red-600"
                            : "text-muted-foreground"
                        )}
                      >
                        {factor.meets_threshold ? "⚠️" : "✓"}{" "}
                        {(factor.weight * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Value: {factor.value.toFixed(2)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <Alert>
              <AlertDescription className="text-sm">
                Based on {detection.sample_size} recent matches
                {detection.analysis_time_seconds &&
                  detection.analysis_time_seconds > 0 && (
                    <span className="ml-2">
                      • Analysis took{" "}
                      {detection.analysis_time_seconds.toFixed(2)}s
                    </span>
                  )}
              </AlertDescription>
            </Alert>

            <Button
              onClick={() => mutate()}
              disabled={isPending}
              type="submit"
              className="w-full"
            >
              {isPending ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                  Analyzing...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {buttonText()}
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
