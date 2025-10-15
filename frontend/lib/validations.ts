import { z } from "zod";

// Player Search Form Validation
export const playerSearchSchema = z.object({
  searchType: z.enum(["riot_id", "summoner_name"]),
  searchValue: z.string().min(1, "Please enter a player name or Riot ID"),
  platform: z.string().min(1, "Please select a platform"),
});

export type PlayerSearchForm = z.infer<typeof playerSearchSchema>;

// Add Tracked Player Form Validation
export const addTrackedPlayerSchema = z.object({
  searchType: z.enum(["riot_id", "summoner_name"]),
  searchValue: z.string().min(1, "Please enter a player name or Riot ID"),
  platform: z.enum(["eun1", "euw1", "na1", "kr", "br1", "la1", "la2", "oc1", "ru", "tr1", "jp1"]),
});

export type AddTrackedPlayerForm = z.infer<typeof addTrackedPlayerSchema>;
