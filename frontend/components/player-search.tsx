"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Player, PlayerSchema } from "@/lib/schemas";
import { playerSearchSchema, type PlayerSearchForm } from "@/lib/validations";
import { validatedGet } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Search, User, AlertCircle } from "lucide-react";
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
        throw new Error(result.error.message);
      }

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

  const onSubmit = (data: PlayerSearchForm) => {
    mutate(data);
  };

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
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error instanceof Error && error.message
                    ? error.message
                    : "Failed to search for player. Please check your input and try again."}
                </AlertDescription>
              </Alert>
            )}
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
