"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  addTrackedPlayerSchema,
  type AddTrackedPlayerForm,
} from "@/lib/validations";
import { addTrackedPlayer } from "@/lib/api";
import { PlayerSchema } from "@/lib/schemas";
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
import { UserPlus, AlertCircle } from "lucide-react";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { toast } from "sonner";

export function AddTrackedPlayer() {
  const queryClient = useQueryClient();

  const form = useForm<AddTrackedPlayerForm>({
    resolver: zodResolver(addTrackedPlayerSchema),
    defaultValues: {
      searchType: "riot_id",
      searchValue: "",
      platform: "eun1",
    },
  });

  const searchType = form.watch("searchType");

  const { mutate, isPending, error, reset } = useMutation({
    mutationFn: async (data: AddTrackedPlayerForm) => {
      const params =
        data.searchType === "riot_id"
          ? { riot_id: data.searchValue.trim(), platform: data.platform }
          : { summoner_name: data.searchValue.trim(), platform: data.platform };

      const result = await addTrackedPlayer(params);

      if (!result.success) {
        throw new Error(result.error.message);
      }

      // Validate the response
      const parsed = PlayerSchema.safeParse(result.data);
      if (!parsed.success) {
        throw new Error("Invalid player data received from server");
      }

      return parsed.data;
    },
    onSuccess: (player) => {
      // Invalidate tracked players list to refresh
      queryClient.invalidateQueries({ queryKey: ["tracked-players"] });

      // Show success toast
      toast.success(
        `Successfully added ${player.summoner_name} to tracked players!`,
      );

      // Reset form
      form.reset({
        searchType: form.getValues("searchType"),
        searchValue: "",
        platform: form.getValues("platform"),
      });

      // Clear error state
      reset();
    },
    onError: () => {
      // Error is already captured in the mutation
      // We'll display it below the form
    },
  });

  const onSubmit = (data: AddTrackedPlayerForm) => {
    mutate(data);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center space-x-2">
          <UserPlus className="h-5 w-5 text-primary" />
          <CardTitle>Add Tracked Player</CardTitle>
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
                  {searchType === "summoner_name" && (
                    <p className="text-xs text-muted-foreground">
                      Note: Summoner name search only works for players already
                      in the database. Use Riot ID for new players.
                    </p>
                  )}
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
                  Adding Player...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Track Player
                </>
              )}
            </Button>

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {error instanceof Error && error.message
                    ? error.message
                    : "Failed to add tracked player. Please check your input and try again."}
                </AlertDescription>
              </Alert>
            )}
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
