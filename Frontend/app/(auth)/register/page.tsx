import type { Metadata } from "next";
import { AuthFrame } from "@/components/auth/AuthFrame";
import RegisterForm from "@/components/auth/RegisterForm";

export const metadata: Metadata = { title: "Create your account" };

export default function RegisterPage() {
  return <AuthFrame title="Create your account"><RegisterForm /></AuthFrame>;
}
