import type { Metadata } from "next";
import { Suspense } from "react";
import AnalyzeWorkspace from "@/components/analyze/AnalyzeWorkspace";

export const metadata: Metadata = { title: "Analyze" };

export default function AnalyzePage() {
  return (
    <Suspense>
      <AnalyzeWorkspace />
    </Suspense>
  );
}
