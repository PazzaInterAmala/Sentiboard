import type { Metadata } from "next";
import { notFound } from "next/navigation";
import QueryView from "@/components/queries/QueryView";

export const metadata: Metadata = { title: "Results" };

export default async function QueryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const queryId = Number(id);
  if (!Number.isInteger(queryId) || queryId < 1) notFound();
  return <QueryView id={queryId} />;
}
