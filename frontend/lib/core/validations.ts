import { z } from "zod";

// Shared validation refinement function
const playerNameRefinement = (val: string) => {
  const trimmed = val.trim();

  // Riot ID format: name#tag
  if (trimmed.includes("#")) {
    const parts = trimmed.split("#");

    // Validate exactly one # symbol
    if (parts.length !== 2) {
      return false; // Multiple or trailing # symbols
    }

    const [name, tag] = parts;
    return (
      name &&
      name.length >= 3 &&
      name.length <= 16 &&
      tag &&
      tag.length >= 1 &&
      tag.length <= 6
    );
  }

  // Summoner name: 3-16 characters
  return trimmed.length >= 3 && trimmed.length <= 16;
};

// Shared player name validation schema
const playerNameValidation = z
  .string()
  .min(1, "Player name is required")
  .transform((val) => val.trim()) // Trim before validation
  .refine(playerNameRefinement, {
    message:
      "Invalid format. Use 'Name#TAG' (tag max 6 chars) or summoner name (3-16 chars)",
  });

// Shared platform enum
const platformEnum = z.enum([
  "eun1",
  "euw1",
  "na1",
  "kr",
  "br1",
  "la1",
  "la2",
  "oc1",
  "ru",
  "tr1",
  "jp1",
  "ph2",
  "sg2",
  "th2",
  "tw2",
  "vn2",
]);

// Player Search Form Validation
export const playerSearchSchema = z.object({
  searchValue: playerNameValidation,
  platform: platformEnum,
});

export type PlayerSearchForm = z.infer<typeof playerSearchSchema>;

// Add Tracked Player Form Validation
export const addTrackedPlayerSchema = z.object({
  searchValue: playerNameValidation,
  platform: platformEnum,
});

export type AddTrackedPlayerForm = z.infer<typeof addTrackedPlayerSchema>;
