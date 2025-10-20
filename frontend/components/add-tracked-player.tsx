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
      searchValue: "",
      platform: "eun1",
    },
  });

  const { mutate, isPending, error, reset } = useMutation({
    mutationFn: async (data: AddTrackedPlayerForm) => {
      // Smart format detection
      const isRiotId = data.searchValue.includes("#");
      const params = isRiotId
        ? { riot_id: data.searchValue, platform: data.platform }
        : { summoner_name: data.searchValue, platform: data.platform };

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
        `Successfully added ${player.summoner_name} to tracked players!`
      );

      // Reset form
      form.reset({
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

  {
    /* TODO [SPY-66]: Change design and layout to be the same as Player Search  */
  }
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
              name="searchValue"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Player Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Player#TAG or SummonerName"
                      disabled={isPending}
                      {...field}
                    />
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
