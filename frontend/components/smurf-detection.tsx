"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  DetectionResponseSchema,
  type DetectionResponse,
  type DetectionRequest,
} from "@/lib/schemas";
import { validatedPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SmurfDetectionProps {
  puuid: string;
}

export function SmurfDetection({ puuid }: SmurfDetectionProps) {
  const [detection, setDetection] = useState<DetectionResponse | null>(null);

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
      }
    },
  });

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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-purple-600" />
          Smurf Detection
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!detection ? (
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
                  "Run Smurf Detection"
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
                  Re-analyzing...
                </>
              ) : (
                "Re-run Analysis"
              )}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
