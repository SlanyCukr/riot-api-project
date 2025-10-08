import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { DetectionResponse, DetectionRequest } from '../types/api';
import { AlertTriangle, CheckCircle, Activity } from 'lucide-react';

interface SmurfDetectionProps {
  puuid: string;
}

export function SmurfDetection({ puuid }: SmurfDetectionProps) {
  const [detection, setDetection] = useState<DetectionResponse | null>(null);
  const { loading, error, post } = useApi<DetectionResponse>();

  const runDetection = async () => {
    const request: DetectionRequest = {
      puuid,
      min_games: 30,
      queue_filter: 420, // Ranked Solo/Duo
      force_reanalyze: true
    };

    await post('/analyze', request, {
      onSuccess: (data) => {
        if (data) {
          setDetection(data);
        }
      }
    });
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high': return 'text-red-600 bg-red-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-blue-600 bg-blue-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600';
    if (score >= 0.6) return 'text-yellow-600';
    if (score >= 0.4) return 'text-blue-600';
    return 'text-gray-600';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center mb-4">
        <Activity className="w-6 h-6 mr-2 text-purple-600" />
        <h2 className="text-xl font-semibold">Smurf Detection</h2>
      </div>

      {!detection ? (
        <div className="text-center py-8">
          <button
            onClick={runDetection}
            disabled={loading}
            className="bg-purple-600 text-white py-2 px-6 rounded-md hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Analyzing...' : 'Run Smurf Detection'}
          </button>
          {error && (
            <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md text-sm">
              {error}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Detection Result Header */}
          <div className="flex items-center justify-between p-4 rounded-lg border-2"
               style={{ borderColor: detection.is_smurf ? '#ef4444' : '#10b981' }}>
            <div className="flex items-center">
              {detection.is_smurf ? (
                <AlertTriangle className="w-8 h-8 text-red-600 mr-3" />
              ) : (
                <CheckCircle className="w-8 h-8 text-green-600 mr-3" />
              )}
              <div>
                <h3 className="text-lg font-semibold">
                  {detection.is_smurf ? 'Smurf Detected' : 'No Smurf Indicators'}
                </h3>
                <p className="text-sm text-gray-600">{detection.reason}</p>
              </div>
            </div>
            <div className="text-right">
              <div className={`text-2xl font-bold ${getScoreColor(detection.detection_score)}`}>
                {(detection.detection_score * 100).toFixed(0)}%
              </div>
              <div className={`text-xs px-2 py-1 rounded-full ${getConfidenceColor(detection.confidence_level)}`}>
                {detection.confidence_level.toUpperCase()} confidence
              </div>
            </div>
          </div>

          {/* Detection Factors */}
          <div>
            <h4 className="font-medium mb-3">Detection Factors:</h4>
            <div className="space-y-2">
              {detection.factors.map((factor, index) => (
                <div key={index} className="flex justify-between items-center p-3 bg-gray-50 rounded-md">
                  <div>
                    <div className="font-medium text-sm">{factor.name.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                    <div className="text-xs text-gray-600">{factor.description}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-sm font-medium ${factor.meets_threshold ? 'text-red-600' : 'text-gray-600'}`}>
                      {factor.meets_threshold ? '⚠️' : '✓'} {(factor.weight * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-gray-500">
                      Value: {factor.value.toFixed(2)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Sample Info */}
          <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded-md">
            Based on {detection.sample_size} recent matches
            {detection.analysis_time_seconds && (
              <span className="ml-2">
                • Analysis took {detection.analysis_time_seconds.toFixed(2)}s
              </span>
            )}
          </div>

          <button
            onClick={runDetection}
            disabled={loading}
            className="w-full bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? 'Re-analyzing...' : 'Re-run Analysis'}
          </button>
        </div>
      )}
    </div>
  );
}
