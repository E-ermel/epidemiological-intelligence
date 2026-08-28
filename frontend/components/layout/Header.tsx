import Link from "next/link";
import { ShieldPlus } from "lucide-react";
import { APP_NAME, APP_SUBTITLE } from "@/lib/constants";
import { Navigation } from "@/components/layout/Navigation";

export function Header() {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <div className="page-shell flex flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600 text-white">
            <ShieldPlus className="h-5 w-5" strokeWidth={2} />
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-sm font-semibold text-foreground sm:text-base">
              {APP_NAME}
            </span>
            <span className="text-xs text-muted">{APP_SUBTITLE}</span>
          </span>
        </Link>

        <Navigation />
      </div>
    </header>
  );
}
