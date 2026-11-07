"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
import { getAuthValidationConfig, passwordRequirements } from "@/lib/auth-config";
import { createRegisterSchema, type RegisterValues } from "@/lib/validation";
import { AuthTabs, FieldError, FormAlert, SubmitButton } from "@/components/auth/AuthFrame";

const validationConfig = getAuthValidationConfig();

export default function RegisterForm() {
  const router = useRouter();
  const [formError, setFormError] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterValues>({
    resolver: zodResolver(createRegisterSchema()),
    mode: "onBlur",
  });

  const onSubmit = async ({ confirmPassword: _confirmPassword, ...credentials }: RegisterValues) => {
    setFormError("");
    try {
      await api.register(credentials);
      router.replace("/dashboard");
      router.refresh();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Unable to create your account. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <AuthTabs active="register" />
      <FormAlert>{formError}</FormAlert>
      <div className="space-y-4">
        <div>
          <label htmlFor="register-username" className="mb-2 block text-xs font-semibold">Username</label>
          <input id="register-username" autoComplete="username" maxLength={validationConfig.usernameMaxLength} placeholder="Choose a username" aria-invalid={Boolean(errors.username)} aria-describedby={errors.username ? "register-username-error" : undefined} {...register("username")} className="h-11 w-full rounded-md border border-[#e9e5dc] bg-white px-3.5 text-sm outline-none placeholder:text-[#a1a8ad] focus:border-accent focus:ring-2 focus:ring-accent/10" />
          <FieldError id="register-username-error">{errors.username?.message}</FieldError>
        </div>
        <div>
          <label htmlFor="register-email" className="mb-2 block text-xs font-semibold">Email address</label>
          <input id="register-email" type="email" autoComplete="email" inputMode="email" placeholder="name@company.com" aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "register-email-error" : undefined} {...register("email")} className="h-11 w-full rounded-md border border-[#e9e5dc] bg-white px-3.5 text-sm outline-none placeholder:text-[#a1a8ad] focus:border-accent focus:ring-2 focus:ring-accent/10" />
          <FieldError id="register-email-error">{errors.email?.message}</FieldError>
        </div>
        <div>
          <label htmlFor="register-password" className="mb-2 block text-xs font-semibold">Create a password</label>
          <div className="relative">
            <input id="register-password" type={showPassword ? "text" : "password"} autoComplete="new-password" aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "register-password-error" : "password-help"} {...register("password")} className="h-11 w-full rounded-md border border-[#e9e5dc] bg-white px-3.5 pr-16 text-sm outline-none placeholder:text-[#a1a8ad] focus:border-accent focus:ring-2 focus:ring-accent/10" />
            <button type="button" onClick={() => setShowPassword((shown) => !shown)} className="absolute inset-y-0 right-0 px-3 text-xs font-medium text-muted hover:text-ink" aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? "Hide" : "Show"}</button>
          </div>
          <FieldError id="register-password-error">{errors.password?.message}</FieldError>
          <p id="password-help" className="mt-2 text-xs leading-5 text-muted">Password requirements: {passwordRequirements(validationConfig).join(" · ")}.</p>
        </div>
        <div>
          <label htmlFor="register-confirm-password" className="mb-2 block text-xs font-semibold">Confirm password</label>
          <input id="register-confirm-password" type="password" autoComplete="new-password" aria-invalid={Boolean(errors.confirmPassword)} aria-describedby={errors.confirmPassword ? "register-confirm-error" : undefined} {...register("confirmPassword")} className="h-11 w-full rounded-md border border-[#e9e5dc] bg-white px-3.5 text-sm outline-none placeholder:text-[#a1a8ad] focus:border-accent focus:ring-2 focus:ring-accent/10" />
          <FieldError id="register-confirm-error">{errors.confirmPassword?.message}</FieldError>
        </div>
      </div>
      <SubmitButton loading={isSubmitting}>Create account</SubmitButton>
      <p className="mt-6 text-center text-sm text-muted">Already have an account? <Link href="/login" className="font-medium text-ink hover:underline">Sign in</Link></p>
    </form>
  );
}
