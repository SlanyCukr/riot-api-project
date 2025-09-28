import { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { Match, MatchListResponse } from '../types/api';
import { Gamepad2, Clock } from 'lucide-react';

interface MatchHistoryProps {
  puuid: string;
  queueFilter?: number;
}

export function MatchHistory({ puuid, queueFilter }: MatchHistoryProps) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const { loading, error, request } = useApi<MatchListResponse>();

  const loadMatches = async () => {
    const start = page * 20;
    await request(`/matches/player/${puuid}?start=${start}&count=20${queueFilter ? `&queue=${queueFilter}` : ''}`, {
      onSuccess: (data) => {
        if (data?.matches) {
          setMatches(prev => [...prev, ...data.matches]);
          setHasMore(data.start + data.count < data.total);
          setPage(prev => prev + 1);
        }
      }
    });
  };

  const getQueueName = (queueId: number) => {
    const queues: Record<number, string> = {
      420: 'Ranked Solo/Duo',
      440: 'Ranked Flex',
      450: 'ARAM',
      400: 'Normal Draft',
      430: 'Normal Blind',
    };
    return queues[queueId] || `Queue ${queueId}`;
  };

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleDateString();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center mb-4">
        <Gamepad2 className="w-6 h-6 mr-2 text-green-600" />
        <h2 className="text-xl font-semibold">Match History</h2>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {matches.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            {loading ? 'Loading matches...' : 'No matches found'}
          </div>
        ) : (
          matches.map((match) => (
            <div key={match.match_id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="font-medium text-gray-900">{match.queue_id && getQueueName(match.queue_id)}</div>
                  <div className="text-sm text-gray-600">{match.game_version}</div>
                  {match.game_mode && (
                    <div className="text-xs text-gray-500">{match.game_mode}</div>
                  )}
                </div>
                <div className="text-right text-sm">
                  <div className="flex items-center text-gray-600">
                    <Clock className="w-3 h-3 mr-1" />
                    {formatDuration(match.game_duration)}
                  </div>
                  <div className="text-xs text-gray-500">{formatDate(match.game_creation)}</div>
                  {match.is_processed && (
                    <div className="text-xs text-green-600">Processed</div>
                  )}
                </div>
              </div>
              <div className="text-xs text-gray-500 font-mono">{match.match_id}</div>
            </div>
          ))
        )}
      </div>

      {matches.length > 0 && hasMore && (
        <button
          onClick={loadMatches}
          disabled={loading}
          className="w-full mt-4 bg-gray-100 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-200 disabled:bg-gray-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Loading...' : 'Load More'}
        </button>
      )}

      {matches.length === 0 && !loading && (
        <button
          onClick={loadMatches}
          disabled={loading}
          className="w-full mt-4 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          Load Matches
        </button>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md">
          {error}
        </div>
      )}
    </div>
  );
}