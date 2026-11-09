function positiveInteger(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function isEnabled(value: string | undefined, fallback: boolean): boolean {
  if (value === undefined) return fallback;
  return value.toLowerCase() === "true" || value === "1";
}

export function getAuthValidationConfig() {
  const usernameMinLength = positiveInteger(process.env.NEXT_PUBLIC_USERNAME_MIN_LENGTH, 3);
  const usernameMaxLength = Math.max(usernameMinLength, positiveInteger(process.env.NEXT_PUBLIC_USERNAME_MAX_LENGTH, 50));
  return {
    usernameMinLength,
    usernameMaxLength,
    passwordMinLength: positiveInteger(process.env.NEXT_PUBLIC_PASSWORD_MIN_LENGTH, 8),
    requireUppercase: isEnabled(process.env.NEXT_PUBLIC_PASSWORD_REQUIRE_UPPERCASE, true),
    requireNumber: isEnabled(process.env.NEXT_PUBLIC_PASSWORD_REQUIRE_NUMBER, true),
    requireSpecial: isEnabled(process.env.NEXT_PUBLIC_PASSWORD_REQUIRE_SPECIAL, false),
  };
}

export function passwordRequirements(config = getAuthValidationConfig()): string[] {
  return [
    `At least ${config.passwordMinLength} characters`,
    ...(config.requireUppercase ? ["One uppercase letter"] : []),
    ...(config.requireNumber ? ["One number"] : []),
    ...(config.requireSpecial ? ["One special character"] : []),
  ];
}
