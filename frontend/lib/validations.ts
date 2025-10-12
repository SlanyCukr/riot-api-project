import { z } from "zod";

// Player Search Form Validation
export const playerSearchSchema = z.object({
  searchType: z.enum(["riot_id", "summoner_name"]),
  searchValue: z.string().min(1, "Please enter a player name or Riot ID"),
  platform: z.string().min(1, "Please select a platform"),
});

export type PlayerSearchForm = z.infer<typeof playerSearchSchema>;
