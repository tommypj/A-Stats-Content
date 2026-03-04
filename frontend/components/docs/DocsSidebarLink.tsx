"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface DocsSidebarLinkProps {
  href: string;
  children: React.ReactNode;
}

export default function DocsSidebarLink({ href, children }: DocsSidebarLinkProps) {
  const pathname = usePathname();
  // Strip locale prefix for comparison
  const cleanPath = pathname.replace(/^\/[a-z]{2}(?=\/)/, "");
  const isActive = cleanPath === href;

  return (
    <Link
      href={href}
      className={cn(
        "block text-sm py-1 pl-3 border-l-2 transition-colors",
        isActive
          ? "border-primary-500 text-primary-600 font-medium"
          : "border-transparent text-text-muted hover:text-text-primary hover:border-cream-300"
      )}
    >
      {children}
    </Link>
  );
}
