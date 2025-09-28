import { useState } from 'react';
import { PlayerSearch } from '../components/PlayerSearch';
import { PlayerCard } from '../components/PlayerCard';
import { MatchHistory } from '../components/MatchHistory';
import { SmurfDetection } from '../components/SmurfDetection';
import { Player } from '../types/api';

export function Dashboard() {
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [showMatchHistory, setShowMatchHistory] = useState(false);
  const [showSmurfDetection, setShowSmurfDetection] = useState(false);

  const handlePlayerFound = (player: Player) => {
    setSelectedPlayer(player);
    setShowMatchHistory(false);
    setShowSmurfDetection(false);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Riot API Smurf Detection
          </h1>
          <p className="text-gray-600">
            Analyze League of Legends players for smurf behavior using match history and performance metrics
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Search Column */}
          <div className="lg:col-span-1">
            <PlayerSearch onPlayerFound={handlePlayerFound} />
          </div>

          {/* Results Column */}
          <div className="lg:col-span-2 space-y-6">
            {selectedPlayer && (
              <>
                <PlayerCard
                  player={selectedPlayer}
                  onAnalyze={() => {
                    setShowMatchHistory(false);
                    setShowSmurfDetection(true);
                  }}
                />

                <div className="flex space-x-4">
                  <button
                    onClick={() => {
                      setShowMatchHistory(!showMatchHistory);
                      setShowSmurfDetection(false);
                    }}
                    className={`px-4 py-2 rounded-md ${
                      showMatchHistory
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    Match History
                  </button>
                  <button
                    onClick={() => {
                      setShowSmurfDetection(!showSmurfDetection);
                      setShowMatchHistory(false);
                    }}
                    className={`px-4 py-2 rounded-md ${
                      showSmurfDetection
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    Smurf Detection
                  </button>
                </div>

                {showMatchHistory && (
                  <MatchHistory puuid={selectedPlayer.puuid} queueFilter={420} />
                )}

                {showSmurfDetection && (
                  <SmurfDetection puuid={selectedPlayer.puuid} />
                )}
              </>
            )}

            {!selectedPlayer && (
              <div className="text-center py-12 text-gray-500">
                Search for a player to view their match history and smurf detection analysis
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}