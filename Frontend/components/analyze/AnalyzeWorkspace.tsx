"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { ComponentType, SVGProps } from "react";
import CsvTab from "@/components/analyze/CsvTab";
import RedditTab from "@/components/analyze/RedditTab";
import TextTab from "@/components/analyze/TextTab";
import { TableIcon, TextIcon, ThreadIcon } from "@/components/icons";
import { PageHeader } from "@/components/ui";

type Tab = "text" | "reddit" | "csv";

const TABS: Array<{ id: Tab; label: string; icon: ComponentType<SVGProps<SVGSVGElement>>; description: string }> = [
  { id: "text", label: "Text", icon: TextIcon, description: "Discover the sentiment behind text, reviews and online conversations." },
  { id: "reddit", label: "Reddit", icon: ThreadIcon, description: "Discover the sentiment behind public discussion and community threads." },
  { id: "csv", label: "CSV Upload", icon: TableIcon, description: "Discover the sentiment behind a whole file of reviews, comments or survey answers." },
];

function isTab(value: string | null): value is Tab {
  return value === "text" || value === "reddit" || value === "csv";
}

export default function AnalyzeWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const requested = searchParams.get("tab");
  const tab: Tab = isTab(requested) ? requested : "text";
  const current = TABS.find((t) => t.id === tab)!;

  const select = (next: Tab) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "text") params.delete("tab"); else params.set("tab", next);
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  };

  return (
    <div>
      <PageHeader
        title="Understand what people think."
        description={current.description}
        aside={
          <div role="tablist" aria-label="Analysis source" className="inline-flex shrink-0 self-start rounded-md border border-line bg-sand p-1 md:self-end">
            {TABS.map(({ id, label, icon: Icon }) => {
              const active = id === tab;
              return (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  id={`tab-${id}`}
                  aria-selected={active}
                  aria-controls={`panel-${id}`}
                  onClick={() => select(id)}
                  className={`flex items-center gap-2 rounded px-3.5 py-2 text-sm font-medium transition-colors duration-150 sm:px-4 ${active ? "bg-ink text-ivory" : "text-charcoal hover:text-ink"}`}
                >
                  <Icon className="size-[18px]" />
                  {label}
                </button>
              );
            })}
          </div>
        }
      />
      <section role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="mt-10 lg:mt-14">
        {tab === "text" && <TextTab />}
        {tab === "reddit" && <RedditTab />}
        {tab === "csv" && <CsvTab />}
      </section>
    </div>
  );
}
