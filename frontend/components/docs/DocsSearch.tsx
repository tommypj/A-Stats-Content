"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Fuse from "fuse.js";
import { Search, FileText } from "lucide-react";
import type { SearchableDoc } from "@/lib/docs";

interface DocsSearchProps {
  articles: SearchableDoc[];
  linkPrefix: string; // "/docs" or "/help"
}

export default function DocsSearch({ articles, linkPrefix }: DocsSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchableDoc[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const fuse = useRef(
    new Fuse(articles, {
      keys: [
        { name: "title", weight: 2 },
        { name: "description", weight: 1 },
        { name: "categoryTitle", weight: 0.5 },
      ],
      threshold: 0.4,
      includeScore: true,
    })
  );

  const handleSearch = useCallback(
    (value: string) => {
      setQuery(value);
      if (value.trim().length < 2) {
        setResults([]);
        setIsOpen(false);
        return;
      }
      const found = fuse.current.search(value).slice(0, 8).map((r) => r.item);
      setResults(found);
      setIsOpen(found.length > 0);
      setSelectedIndex(0);
    },
    []
  );

  const navigate = useCallback(
    (article: SearchableDoc) => {
      const href = `${linkPrefix}/${article.category}/${article.slug}`;
      router.push(href);
      setQuery("");
      setIsOpen(false);
    },
    [router, linkPrefix]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && results[selectedIndex]) {
        e.preventDefault();
        navigate(results[selectedIndex]);
      } else if (e.key === "Escape") {
        setIsOpen(false);
      }
    },
    [isOpen, results, selectedIndex, navigate]
  );

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard shortcut: Ctrl+K or Cmd+K
  useEffect(() => {
    function handleGlobalKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    document.addEventListener("keydown", handleGlobalKey);
    return () => document.removeEventListener("keydown", handleGlobalKey);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search docs... (Ctrl+K)"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          className="w-full pl-9 pr-4 py-2.5 text-sm bg-white border border-cream-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-300 text-text-primary placeholder:text-text-muted"
        />
      </div>

      {isOpen && (
        <div className="absolute top-full mt-2 w-full bg-white rounded-xl border border-cream-200 shadow-soft-lg overflow-hidden z-50">
          {results.map((article, i) => (
            <button
              key={`${article.category}/${article.slug}`}
              onClick={() => navigate(article)}
              className={`w-full flex items-start gap-3 px-4 py-3 text-left transition-colors ${
                i === selectedIndex ? "bg-primary-50" : "hover:bg-surface-secondary"
              }`}
            >
              <FileText className="h-4 w-4 text-primary-400 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  {article.title}
                </p>
                <p className="text-xs text-text-muted truncate">
                  {article.categoryTitle} &middot; {article.description}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
