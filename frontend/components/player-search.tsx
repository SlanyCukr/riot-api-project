"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search, User, AlertCircle, UserPlus, Loader2 } from "lucide-react";
import { z } from "zod";

import { Player, PlayerSchema } from "@/lib/schemas";
import { playerSearchSchema, type PlayerSearchForm } from "@/lib/validations";
import {
  validatedGet,
  addTrackedPlayer,
  searchPlayerSuggestions,
} from "@/lib/api";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

// Constants for autocomplete behavior
const SUGGESTION_DEBOUNCE_MS = 300;
const MIN_SEARCH_LENGTH = 3;

interface PlayerSearchProps {
  onPlayerFound: (player: Player) => void;
}

export function PlayerSearch({ onPlayerFound }: PlayerSearchProps) {
  const [showTrackOption, setShowTrackOption] = useState(false);
  const [lastSearchParams, setLastSearchParams] =
    useState<PlayerSearchForm | null>(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [debouncedSearchValue, setDebouncedSearchValue] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  const form = useForm<PlayerSearchForm>({
    resolver: zodResolver(playerSearchSchema),
    defaultValues: {
      searchValue: "",
      platform: "eun1",
    },
  });

  // eslint-disable-next-line react-hooks/incompatible-library -- React Hook Form watch() is intentionally not memoizable
  const searchValue = form.watch("searchValue");
  const platform = form.watch("platform");

  // Debounce search value for autocomplete
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchValue(searchValue);
    }, SUGGESTION_DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [searchValue]);

  // Fetch suggestions when debounced value changes
  const { data: suggestionsResult, isLoading: suggestionsLoading } = useQuery({
    queryKey: ["player-suggestions", debouncedSearchValue, platform],
    queryFn: async () => {
      if (debouncedSearchValue.length < MIN_SEARCH_LENGTH) {
        return { success: true as const, data: [] };
      }

      const result = await searchPlayerSuggestions({
        q: debouncedSearchValue,
        platform: platform,
        limit: 5,
      });

      return result;
    },
    enabled: debouncedSearchValue.length >= MIN_SEARCH_LENGTH,
  });

  const suggestions = useMemo(() => {
    return suggestionsResult?.success ? suggestionsResult.data : [];
  }, [suggestionsResult]);

  // Show suggestions when there are results and input is focused
  useEffect(() => {
    if (suggestions.length > 0 && searchValue.length >= MIN_SEARCH_LENGTH) {
      setShowSuggestions(true);
      setSelectedIndex(-1);
    } else {
      setShowSuggestions(false);
    }
  }, [suggestions, searchValue]);

  // Handle suggestion selection
  const handleSelectSuggestion = useCallback(
    (player: Player) => {
      setShowSuggestions(false);
      setSelectedIndex(-1);
      onPlayerFound(player);
      form.reset({
        searchValue: "",
        platform: form.getValues("platform"),
      });
    },
    [form, onPlayerFound],
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!showSuggestions || suggestions.length === 0) return;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : prev,
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
          break;
        case "Enter":
          if (selectedIndex >= 0) {
            e.preventDefault();
            handleSelectSuggestion(suggestions[selectedIndex]);
          }
          break;
        case "Escape":
          e.preventDefault();
          setShowSuggestions(false);
          setSelectedIndex(-1);
          break;
      }
    },
    [showSuggestions, suggestions, selectedIndex, handleSelectSuggestion],
  );

  const { mutate, isPending, error } = useMutation({
    mutationFn: async (data: PlayerSearchForm) => {
      setLastSearchParams(data);

      // Use single query parameter for fuzzy search
      const params = {
        query: data.searchValue,
        platform: data.platform,
      };

      const result = await validatedGet(
        z.array(PlayerSchema),
        "/players/search",
        params,
      );

      if (!result.success) {
        throw new Error(result.error.message);
      }

      // Check if results are empty (player not found)
      if (result.data.length === 0) {
        setShowTrackOption(true);
        throw new Error("PLAYER_NOT_FOUND");
      }

      setShowTrackOption(false);
      // Return the first result (best match)
      return result.data[0];
    },
    onSuccess: (player) => {
      onPlayerFound(player);
      form.reset({
        searchValue: "",
        platform: form.getValues("platform"),
      });
    },
  });

  const trackMutation = useMutation({
    mutationFn: async (): Promise<Player | null> => {
      if (!lastSearchParams) return null;

      // Use the same logic for addTrackedPlayer (uses riot_id or summoner_name)
      const isRiotId = lastSearchParams.searchValue.includes("#");
      const params = isRiotId
        ? {
            riot_id: lastSearchParams.searchValue,
            platform: lastSearchParams.platform,
          }
        : {
            summoner_name: lastSearchParams.searchValue,
            platform: lastSearchParams.platform,
          };

      const result = await addTrackedPlayer(params);
      if (!result.success) {
        throw new Error(result.error.message);
      }
      return result.data as Player;
    },
    onSuccess: (player) => {
      if (player) {
        setShowTrackOption(false);
        onPlayerFound(player);
        form.reset({
          searchValue: "",
          platform: form.getValues("platform"),
        });
      }
    },
  });

  const onSubmit = useCallback(
    (data: PlayerSearchForm) => {
      mutate(data);
    },
    [mutate],
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center space-x-2">
          <User className="h-5 w-5 text-primary" />
          <CardTitle>Player Search</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="searchValue"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Player Name</FormLabel>
                  <FormControl>
                    <Popover
                      open={showSuggestions}
                      onOpenChange={setShowSuggestions}
                    >
                      <PopoverTrigger asChild>
                        <div className="relative">
                          <Input
                            {...field}
                            ref={inputRef}
                            placeholder="Player#TAG or SummonerName"
                            disabled={isPending}
                            onKeyDown={handleKeyDown}
                            onFocus={() => {
                              if (
                                suggestions.length > 0 &&
                                searchValue.length >= MIN_SEARCH_LENGTH
                              ) {
                                setShowSuggestions(true);
                              }
                            }}
                            onBlur={() => {
                              setShowSuggestions(false);
                            }}
                            autoComplete="off"
                          />
                          {suggestionsLoading &&
                            searchValue.length >= MIN_SEARCH_LENGTH && (
                              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                <Loader2
                                  className="h-4 w-4 animate-spin text-muted-foreground"
                                  aria-label="Loading suggestions"
                                  role="status"
                                />
                              </div>
                            )}
                        </div>
                      </PopoverTrigger>
                      <PopoverContent
                        className="w-[var(--radix-popover-trigger-width)] p-0"
                        align="start"
                        onOpenAutoFocus={(e) => e.preventDefault()}
                      >
                        <div className="max-h-[300px] overflow-y-auto">
                          {suggestions.length === 0 ? (
                            <div className="p-4 text-center text-sm text-muted-foreground">
                              No players found
                            </div>
                          ) : (
                            <div className="py-1">
                              {suggestions.map((suggestion, index) => (
                                <button
                                  key={suggestion.puuid}
                                  type="button"
                                  className={`w-full px-4 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground transition-colors ${
                                    index === selectedIndex
                                      ? "bg-accent text-accent-foreground"
                                      : ""
                                  }`}
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    handleSelectSuggestion(suggestion);
                                  }}
                                  onMouseEnter={() => setSelectedIndex(index)}
                                >
                                  <div className="flex flex-col">
                                    <span className="font-medium">
                                      {suggestion.riot_id && suggestion.tag_line
                                        ? `${suggestion.riot_id}#${suggestion.tag_line}`
                                        : suggestion.summoner_name}
                                    </span>
                                    {suggestion.riot_id &&
                                      suggestion.tag_line &&
                                      suggestion.summoner_name && (
                                        <span className="text-xs text-muted-foreground">
                                          {suggestion.summoner_name}
                                        </span>
                                      )}
                                  </div>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </PopoverContent>
                    </Popover>
                  </FormControl>
                  <p className="text-xs text-muted-foreground">
                    Enter Riot ID (Name#TAG) or summoner name
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="platform"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Platform</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                    disabled={isPending}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a platform" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="eun1">EU Nordic & East</SelectItem>
                      <SelectItem value="euw1">EU West</SelectItem>
                      <SelectItem value="na1">North America</SelectItem>
                      <SelectItem value="kr">Korea</SelectItem>
                      <SelectItem value="br1">Brazil</SelectItem>
                      <SelectItem value="la1">Latin America North</SelectItem>
                      <SelectItem value="la2">Latin America South</SelectItem>
                      <SelectItem value="oc1">Oceania</SelectItem>
                      <SelectItem value="ru">Russia</SelectItem>
                      <SelectItem value="tr1">Turkey</SelectItem>
                      <SelectItem value="jp1">Japan</SelectItem>
                      <SelectItem value="ph2">Philippines</SelectItem>
                      <SelectItem value="sg2">Singapore</SelectItem>
                      <SelectItem value="th2">Thailand</SelectItem>
                      <SelectItem value="tw2">Taiwan</SelectItem>
                      <SelectItem value="vn2">Vietnam</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-4 w-4" />
                  Search Player
                </>
              )}
            </Button>

            {error && (
              <>
                {error instanceof Error &&
                error.message === "PLAYER_NOT_FOUND" &&
                showTrackOption ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Player Not Found in Database</AlertTitle>
                    <AlertDescription>
                      <p className="mb-3">
                        This player hasn&apos;t been tracked yet. Would you like
                        to add them?
                      </p>
                      <Button
                        onClick={() => trackMutation.mutate()}
                        disabled={trackMutation.isPending}
                        variant="default"
                        size="sm"
                      >
                        {trackMutation.isPending ? (
                          <>
                            <div className="mr-2 h-3 w-3 animate-spin rounded-full border-2 border-background border-t-transparent" />
                            Tracking Player...
                          </>
                        ) : (
                          <>
                            <UserPlus className="mr-2 h-3 w-3" />
                            Track Player
                          </>
                        )}
                      </Button>
                    </AlertDescription>
                  </Alert>
                ) : (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {error instanceof Error &&
                      error.message === "PLAYER_NOT_FOUND"
                        ? "Player not found in database."
                        : error instanceof Error && error.message
                          ? error.message
                          : "Failed to search for player. Please check your input and try again."}
                    </AlertDescription>
                  </Alert>
                )}
                {trackMutation.error && (
                  <Alert variant="destructive" className="mt-2">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {trackMutation.error instanceof Error
                        ? trackMutation.error.message
                        : "Failed to track player. Please try again."}
                    </AlertDescription>
                  </Alert>
                )}
              </>
            )}
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
