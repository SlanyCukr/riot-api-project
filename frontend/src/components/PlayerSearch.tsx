import { useState } from "react";
import { useApi } from "../hooks/useApi";
import { Player } from "../types/api";
import { Search, User } from "lucide-react";

interface PlayerSearchProps {
  onPlayerFound: (player: Player) => void;
}

export function PlayerSearch({ onPlayerFound }: PlayerSearchProps) {
  const [searchType, setSearchType] = useState<"riot_id" | "summoner_name">(
    "riot_id",
  );
  const [searchValue, setSearchValue] = useState("");
  const [platform, setPlatform] = useState("eun1");
  const { loading, error, get } = useApi<Player>();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!searchValue.trim()) return;

    const searchParams = {
      [searchType]: searchValue.trim(),
      platform,
    };

    await get("/players/search", searchParams, {
      onSuccess: (data) => {
        if (data) {
          onPlayerFound(data);
        }
      },
    });
  };

  return (
    <div className="w-full max-w-md mx-auto p-6 bg-white rounded-lg shadow-lg">
      <div className="flex items-center mb-4">
        <User className="w-6 h-6 mr-2 text-blue-600" />
        <h2 className="text-xl font-semibold">Player Search</h2>
      </div>

      <form onSubmit={handleSearch} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search Type
          </label>
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="searchType"
                value="riot_id"
                checked={searchType === "riot_id"}
                onChange={(e) => setSearchType(e.target.value as "riot_id")}
                className="mr-2"
              />
              Riot ID (name#tag)
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="searchType"
                value="summoner_name"
                checked={searchType === "summoner_name"}
                onChange={(e) =>
                  setSearchType(e.target.value as "summoner_name")
                }
                className="mr-2"
              />
              Summoner Name
            </label>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            {searchType === "riot_id" ? "Riot ID" : "Summoner Name"}
          </label>
          <input
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder={
              searchType === "riot_id" ? "DangerousDan#EUW" : "DangerousDan"
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Platform
          </label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          >
            <option value="eun1">EU Nordic & East</option>
            <option value="euw1">EU West</option>
            <option value="na1">North America</option>
            <option value="kr">Korea</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading || !searchValue.trim()}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Searching...
            </>
          ) : (
            <>
              <Search className="w-4 h-4 mr-2" />
              Search Player
            </>
          )}
        </button>

        {error && (
          <div className="p-3 bg-red-100 border border-red-400 text-red-700 rounded-md">
            {error}
          </div>
        )}
      </form>
    </div>
  );
}
