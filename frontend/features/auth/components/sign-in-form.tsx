"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import Image from "next/image";
import { useAuth } from "../context/auth-context";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { LoginCredentials } from "../types";

export function SignInForm() {
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<LoginCredentials>({
    defaultValues: {
      email: "",
      password: "",
    },
    mode: "onSubmit",
    reValidateMode: "onSubmit",
  });

  const onSubmit = async (data: LoginCredentials) => {
    setError(null);
    setIsSubmitting(true);

    try {
      await login(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-start justify-center py-12 px-4"
      style={{
        paddingTop: "20vh",
      }}
    >
      <div className="flex items-center gap-12 max-w-5xl w-full">
        {/* Logo Section */}
        <div className="hidden lg:block flex-shrink-0">
          <div className="relative w-[300px] h-[300px]">
            <Image
              src="/logo.png"
              alt="LeaguEyeSpy Logo"
              fill
              sizes="300px"
              className="object-contain"
              priority
            />
          </div>
        </div>

        {/* Form Section */}
        <div className="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Sign In</h1>
            <p className="text-gray-600">
              Enter your credentials to access your account
            </p>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Form {...form}>
            <form
              id="sign-in-form"
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-6"
            >
              <FormField
                control={form.control}
                name="email"
                rules={{
                  required: "Email is required",
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: "Invalid email address",
                  },
                }}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-700">Email</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="email"
                        placeholder="terry.davis@templeos.org"
                        disabled={isSubmitting}
                        className="text-gray-900 border-gray-300 placeholder:text-gray-500 focus-visible:ring-gray-400"
                        style={{ backgroundColor: "#e5e7eb" }}
                        autoComplete="email"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                rules={{
                  required: "Password is required",
                }}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-gray-700">Password</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="password"
                        placeholder="••••••••"
                        disabled={isSubmitting}
                        className="text-gray-900 border-gray-300 placeholder:text-gray-500 focus-visible:ring-gray-400"
                        style={{ backgroundColor: "#e5e7eb" }}
                        autoComplete="current-password"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" disabled={isSubmitting} className="w-full">
                {isSubmitting ? "Signing in..." : "Sign In"}
              </Button>
            </form>
          </Form>
        </div>
      </div>
    </div>
  );
}
