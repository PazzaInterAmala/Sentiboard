import { z } from "zod";
import { getAuthValidationConfig } from "@/lib/auth-config";

export function createEmailSchema() {
  return z.string().trim().min(1, "Enter your email address.").email("Enter a valid email address.");
}

export function createPasswordSchema() {
  const config = getAuthValidationConfig();
  let schema = z.string().min(config.passwordMinLength, `Use at least ${config.passwordMinLength} characters.`);
  if (config.requireUppercase) schema = schema.regex(/[A-Z]/, "Add at least one uppercase letter.");
  if (config.requireNumber) schema = schema.regex(/[0-9]/, "Add at least one number.");
  if (config.requireSpecial) schema = schema.regex(/[^A-Za-z0-9]/, "Add at least one special character.");
  return schema;
}

export function createLoginSchema() {
  return z.object({ email: createEmailSchema(), password: z.string().min(1, "Enter your password.") });
}

export function createRegisterSchema() {
  const config = getAuthValidationConfig();
  return z.object({
    username: z.string().trim()
      .min(config.usernameMinLength, `Username must be at least ${config.usernameMinLength} characters.`)
      .max(config.usernameMaxLength, `Username must be ${config.usernameMaxLength} characters or fewer.`)
      .regex(/^[a-zA-Z0-9_.-]+$/, "Use letters, numbers, dots, underscores, or hyphens."),
    email: createEmailSchema(),
    password: createPasswordSchema(),
    confirmPassword: z.string().min(1, "Confirm your password."),
  }).refine((data) => data.password === data.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords do not match.",
  });
}

export type LoginValues = z.infer<ReturnType<typeof createLoginSchema>>;
export type RegisterValues = z.infer<ReturnType<typeof createRegisterSchema>>;
