import { Player } from '../types/api';
import { Trophy, User } from 'lucide-react';

interface PlayerCardProps {
  player: Player;
  onAnalyze?: () => void;
}

export function PlayerCard({ player, onAnalyze }: PlayerCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center">
          <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mr-4">
            <User className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold">{player.summoner_name}</h3>
            {player.riot_id && (
              <p className="text-sm text-gray-600">{player.riot_id}</p>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="flex items-center text-sm text-gray-600">
            <Trophy className="w-4 h-4 mr-1" />
            Level {player.account_level}
          </div>
          <div className="text-xs text-gray-500 mt-1">{player.platform}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-gray-600">PUUID:</span>
          <div className="font-mono text-xs bg-gray-100 p-1 rounded mt-1 truncate">
            {player.puuid}
          </div>
        </div>
        <div>
          <span className="text-gray-600">First Seen:</span>
          <div className="text-xs">{formatDate(player.created_at)}</div>
        </div>
        <div>
          <span className="text-gray-600">Last Seen:</span>
          <div className="text-xs">{formatDate(player.last_seen)}</div>
        </div>
        <div>
          <span className="text-gray-600">Platform:</span>
          <div className="text-xs">{player.platform}</div>
        </div>
      </div>

      {onAnalyze && (
        <button
          onClick={onAnalyze}
          className="w-full mt-4 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
        >
          Analyze for Smurf Detection
        </button>
      )}
    </div>
  );
}