import { Player } from "@/lib/schemas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { User } from "lucide-react";
import { TrackPlayerButton } from "@/components/track-player-button";

interface PlayerCardProps {
  player: Player;
}

export function PlayerCard({ player }: PlayerCardProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center space-x-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <User className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-xl">
                  {player.riot_id && player.tag_line
                    ? `${player.riot_id}#${player.tag_line}`
                    : player.summoner_name}
                </CardTitle>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{player.platform.toUpperCase()}</span>
                  <Badge variant="secondary">
                    Level {player.account_level}
                  </Badge>
                  {player.is_tracked && (
                    <Badge variant="default" className="bg-yellow-600">
                      Tracked
                    </Badge>
                  )}
                </div>
              </div>
              <TrackPlayerButton
                puuid={player.puuid}
                playerName={
                  player.riot_id && player.tag_line
                    ? `${player.riot_id}#${player.tag_line}`
                    : player.summoner_name
                }
                variant="outline"
                size="default"
              />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="font-medium text-muted-foreground">PUUID</p>
            <p className="font-mono text-xs">{player.puuid.slice(0, 20)}...</p>
          </div>
          <div>
            <p className="font-medium text-muted-foreground">Last Seen</p>
            <p>{formatDate(player.last_seen)}</p>
          </div>
          <div>
            <p className="font-medium text-muted-foreground">Account Created</p>
            <p>{formatDate(player.created_at)}</p>
          </div>
          <div>
            <p className="font-medium text-muted-foreground">Platform</p>
            <p className="uppercase">{player.platform}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
