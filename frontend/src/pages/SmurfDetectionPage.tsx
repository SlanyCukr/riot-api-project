import { useState } from "react";
import { PlayerSearch } from "../components/PlayerSearch";
import { PlayerCard } from "../components/PlayerCard";
import { MatchHistory } from "../components/MatchHistory";
import { SmurfDetection } from "../components/SmurfDetection";
import { Player } from "../types/api";

export function SmurfDetectionPage() {
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [showMatchHistory, setShowMatchHistory] = useState(false);
  const [showSmurfDetection, setShowSmurfDetection] = useState(false);

  const handlePlayerFound = (player: Player) => {
    setSelectedPlayer(player);
    setShowMatchHistory(false);
    setShowSmurfDetection(false);
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Header Card + Search */}
        <div className="lg:col-span-1 space-y-2">
          {/* Header Card */}
          <div className="bg-navy-light rounded-lg shadow-lg p-6">
            <h1 className="text-2xl font-medium mb-3 text-gold-base">
              Smurf Detection
            </h1>
            <p className="text-white text-sm leading-relaxed">
              Analyze League of Legends players for smurf behavior using match
              history and performance metrics
            </p>
          </div>

          {/* Placeholder text above search */}
          {!selectedPlayer && (
            <div className="text-center py-4 text-gray-700 text-base">
              Search for a player to view their match history and smurf
              detection analysis
            </div>
          )}

          {/* Player Search */}
          <PlayerSearch onPlayerFound={handlePlayerFound} />
        </div>

        {/* Right Column - Results */}
        <div className="lg:col-span-2 space-y-6">
          {selectedPlayer && (
            <>
              <PlayerCard player={selectedPlayer} />

              <div className="flex gap-4">
                <button
                  onClick={() => {
                    setShowMatchHistory(!showMatchHistory);
                    setShowSmurfDetection(false);
                  }}
                  className={`px-6 py-3 rounded-lg font-medium transition-all duration-300 shadow-md hover:shadow-lg ${
                    showMatchHistory
                      ? "bg-navy-base text-white hover:bg-navy-dark"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                >
                  Match History
                </button>
                <button
                  onClick={() => {
                    setShowSmurfDetection(!showSmurfDetection);
                    setShowMatchHistory(false);
                  }}
                  className={`px-6 py-3 rounded-lg font-medium transition-all duration-300 shadow-md hover:shadow-lg ${
                    showSmurfDetection
                      ? "bg-gold-base text-gray-900 hover:bg-gold-dark"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
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
        </div>
      </div>
    </div>
  );
}
