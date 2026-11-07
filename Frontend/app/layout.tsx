import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "SentiBoard", template: "%s | SentiBoard" },
  description: "Understand the sentiment behind customer feedback and online conversations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body className="font-sans antialiased">{children}</body></html>;
}
