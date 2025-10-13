"use client";

import { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  DetectionResponseSchema,
  DetectionExistsResponseSchema,
  type DetectionResponse,
  type DetectionRequest,
} from "@/lib/schemas";
import { validatedPost, validatedGet } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
  Clock,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SmurfDetectionProps {
  puuid: string;
}

// Helper function to format timestamp
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

  // Consider data old if > 24 hours
  const isOld = diffHours > 24;

  return { text, isOld };
}

export function SmurfDetection({ puuid }: SmurfDetectionProps) {
  const [detection, setDetection] = useState<DetectionResponse | null>(null);
  const [showingCached, setShowingCached] = useState(false);

  // Fetch latest detection result (cached)
  const { data: latestDetection, isLoading: isLoadingLatest } = useQuery({
    queryKey: ["latest-detection", puuid],
    queryFn: async () => {
      const result = await validatedGet(
        DetectionResponseSchema,
        `/detection/player/${puuid}/latest`,
      );
      if (!result.success) {
        // 404 is expected if no analysis exists
        if (result.error.status === 404) {
          return null;
        }
        throw new Error(result.error.message);
      }
      return result.data;
    },
    retry: false,
  });

  // Check if analysis exists
  const { data: existsCheck } = useQuery({
    queryKey: ["detection-exists", puuid],
    queryFn: async () => {
      const result = await validatedGet(
        DetectionExistsResponseSchema,
        `/detection/player/${puuid}/exists`,
      );
      if (!result.success) {
        return null;
      }
      return result.data;
    },
    retry: false,
  });

  // Set detection from cache when loaded
  useEffect(() => {
    if (latestDetection && !detection) {
      setDetection(latestDetection);
      setShowingCached(true);
    }
  }, [latestDetection, detection]);

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
        "/detection/analyze",
        request,
      );
    },
    onSuccess: (result) => {
      if (result.success) {
        setDetection(result.data);
        setShowingCached(false); // Now showing fresh data
      }
    },
  });

  // Determine button text and state
  const getButtonText = () => {
    if (isPending) return "Analyzing...";
    if (existsCheck?.exists) return "Update Analysis";
    return "Run Analysis";
  };

  // Get timestamp info if available
  const timestampInfo =
    existsCheck?.exists && existsCheck.last_analysis
      ? formatTimeAgo(existsCheck.last_analysis)
      : null;

  const getConfidenceVariant = (
    confidence: string,
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

  // Show loading state only if we're fetching and have no cached data
  const isInitialLoading = isLoadingLatest && !detection;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-purple-600" />
          Smurf Detection
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isInitialLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : !detection ? (
          <div className="space-y-4">
            <div className="text-center py-8">
              <Button
                onClick={() => mutate()}
                disabled={isPending}
                className="bg-purple-600 hover:bg-purple-700"
              >
                {isPending ? (
                  <>
                    <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                    Analyzing...
                  </>
                ) : (
                  getButtonText()
                )}
              </Button>
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error instanceof Error
                    ? error.message
                    : "Failed to run smurf detection. Please try again."}
                </AlertDescription>
              </Alert>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            {/* Timestamp and Cache Indicator */}
            {showingCached && timestampInfo && (
              <Alert
                className={cn(
                  "border-blue-200 bg-blue-50",
                  timestampInfo.isOld && "border-yellow-200 bg-yellow-50",
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

            {/* Detection Result Header */}
            <div
              className={cn(
                "flex items-center justify-between rounded-lg border-2 p-4",
                detection.is_smurf
                  ? "border-red-500 bg-red-50"
                  : "border-green-500 bg-green-50",
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
                    getScoreColor(detection.detection_score),
                  )}
                >
                  {(detection.detection_score * 100).toFixed(0)}%
                </div>
                <Badge
                  variant={getConfidenceVariant(detection.confidence_level)}
                >
                  {detection.confidence_level.toUpperCase()} confidence
                </Badge>
              </div>
            </div>

            {/* Detection Factors */}
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
                            : "text-muted-foreground",
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

            {/* Sample Info */}
            <Alert>
              <AlertDescription className="text-sm">
                Based on {detection.sample_size} recent matches
                {detection.analysis_time_seconds && (
                  <span className="ml-2">
                    • Analysis took {detection.analysis_time_seconds.toFixed(2)}
                    s
                  </span>
                )}
              </AlertDescription>
            </Alert>

            <Button
              onClick={() => mutate()}
              disabled={isPending}
              className="w-full bg-purple-600 hover:bg-purple-700"
            >
              {isPending ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                  Analyzing...
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {getButtonText()}
                </>
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
