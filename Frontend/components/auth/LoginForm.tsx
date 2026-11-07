"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
import { createLoginSchema, type LoginValues } from "@/lib/validation";
import { AuthTabs, FieldError, FormAlert, SubmitButton } from "@/components/auth/AuthFrame";

export default function LoginForm() {
  const router = useRouter();
  const [formError, setFormError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({
    resolver: zodResolver(createLoginSchema()),
    mode: "onBlur",
  });

  const onSubmit = async (values: LoginValues) => {
    setFormError("");
    try {
      await api.login(values);
      router.replace("/dashboard");
      router.refresh();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to sign in. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <AuthTabs active="login" />
      <FormAlert>{formError}</FormAlert>
      <div className="space-y-5">
        <div>
          <label htmlFor="login-email" className="mb-2 block text-xs font-semibold">Email address</label>
          <input id="login-email" type="email" autoComplete="email" inputMode="email" placeholder="you@company.com" aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "login-email-error" : undefined} {...register("email")} className="h-11 w-full rounded-md border border-[#e9e5dc] bg-white px-3.5 text-sm outline-none placeholder:text-[#a1a8ad] focus:border-accent focus:ring-2 focus:ring-accent/10" />
          <FieldError id="login-email-error">{errors.email?.message}</FieldError>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="login-password" className="text-xs font-semibold">Password</label>
            <span className="text-xs text-muted">Need help? <Link href="/about" className="text-accent hover:underline">Contact support</Link></span>
          </div>
          <div className="relative">
            <input id="login-password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter your password" aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "login-password-error" : undefined} {...register("password")} className="h-11 w-full rounded-md border border-[#e9e5dc] bg-white px-3.5 pr-16 text-sm outline-none placeholder:text-[#a1a8ad] focus:border-accent focus:ring-2 focus:ring-accent/10" />
            <button type="button" onClick={() => setShowPassword((shown) => !shown)} className="absolute inset-y-0 right-0 px-3 text-xs font-medium text-muted hover:text-ink" aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button>
          </div>
          <FieldError id="login-password-error">{errors.password?.message}</FieldError>
        </div>
      </div>
      <SubmitButton loading={isSubmitting}>Sign in to SentiBoard</SubmitButton>
      <p className="mt-6 text-center text-sm text-muted">Need an account? <Link href="/register" className="font-medium text-accent hover:underline">Register</Link></p>
    </form>
  );
}
