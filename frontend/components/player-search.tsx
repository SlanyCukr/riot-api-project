"use client";

import { useState, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Search, User, AlertCircle, UserPlus } from "lucide-react";

import { Player, PlayerSchema } from "@/lib/schemas";
import { playerSearchSchema, type PlayerSearchForm } from "@/lib/validations";
import { validatedGet, addTrackedPlayer } from "@/lib/api";

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

interface PlayerSearchProps {
  onPlayerFound: (player: Player) => void;
}

export function PlayerSearch({ onPlayerFound }: PlayerSearchProps) {
  const [showTrackOption, setShowTrackOption] = useState(false);
  const [lastSearchParams, setLastSearchParams] =
    useState<PlayerSearchForm | null>(null);

  const form = useForm<PlayerSearchForm>({
    resolver: zodResolver(playerSearchSchema),
    defaultValues: {
      searchType: "riot_id",
      searchValue: "",
      platform: "eun1",
    },
  });

  // Extract searchType to avoid React Compiler warning about watch()
  const searchType = form.watch("searchType");

  const { mutate, isPending, error } = useMutation({
    mutationFn: async (data: PlayerSearchForm) => {
      setLastSearchParams(data);
      const params = {
        [data.searchType]: data.searchValue.trim(),
        platform: data.platform,
      };
      const result = await validatedGet(
        PlayerSchema,
        "/players/search",
        params,
      );

      if (!result.success) {
        // Check if it's a 404 (player not in database)
        if (result.error.status === 404) {
          setShowTrackOption(true);
          throw new Error("PLAYER_NOT_FOUND");
        }
        throw new Error(result.error.message);
      }

      setShowTrackOption(false);
      return result.data;
    },
    onSuccess: (player) => {
      onPlayerFound(player);
      form.reset({
        searchType: form.getValues("searchType"),
        searchValue: "",
        platform: form.getValues("platform"),
      });
    },
  });

  const trackMutation = useMutation({
    mutationFn: async (): Promise<Player | null> => {
      if (!lastSearchParams) return null;

      const params: {
        platform: string;
        riot_id?: string;
        summoner_name?: string;
      } = {
        platform: lastSearchParams.platform,
      };

      if (lastSearchParams.searchType === "riot_id") {
        params.riot_id = lastSearchParams.searchValue.trim();
      } else {
        params.summoner_name = lastSearchParams.searchValue.trim();
      }

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
          searchType: form.getValues("searchType"),
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
              name="searchType"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Search Type</FormLabel>
                  <div className="flex gap-4">
                    <label className="flex cursor-pointer items-center gap-2">
                      <input
                        type="radio"
                        value="riot_id"
                        checked={field.value === "riot_id"}
                        onChange={() => field.onChange("riot_id")}
                        className="h-4 w-4"
                      />
                      <span className="text-sm">Riot ID (name#tag)</span>
                    </label>
                    <label className="flex cursor-pointer items-center gap-2">
                      <input
                        type="radio"
                        value="summoner_name"
                        checked={field.value === "summoner_name"}
                        onChange={() => field.onChange("summoner_name")}
                        className="h-4 w-4"
                      />
                      <span className="text-sm">Summoner Name</span>
                    </label>
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="searchValue"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    {searchType === "riot_id" ? "Riot ID" : "Summoner Name"}
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder={
                        searchType === "riot_id"
                          ? "DangerousDan#EUW"
                          : "DangerousDan"
                      }
                      disabled={isPending}
                      {...field}
                    />
                  </FormControl>
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
