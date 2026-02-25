"use client";

import { useState } from "react";
import { Search, Sparkles } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  showExamples?: boolean;
}

const EXAMPLE_QUERIES = [
  "What are the key findings in the latest reports?",
  "Summarize the main topics covered in these documents",
  "What are the best practices mentioned?",
];

export function QueryInput({
  onSubmit,
  isLoading = false,
  placeholder = "Ask anything about your knowledge base...",
  showExamples = false,
}: QueryInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  const handleExampleClick = (example: string) => {
    setQuery(example);
  };

  return (
    <div className="space-y-3">
      <form onSubmit={handleSubmit} className="relative">
        <Textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          rows={4}
          className="pr-14 resize-none"
          disabled={isLoading}
        />
        <Button
          type="submit"
          size="icon"
          className="absolute bottom-3 right-3"
          disabled={!query.trim() || isLoading}
          isLoading={isLoading}
        >
          {!isLoading && <Search className="h-4 w-4" />}
        </Button>
      </form>

      {showExamples && !isLoading && (
        <div className="space-y-2">
          <p className="text-xs text-text-muted flex items-center gap-1">
            <Sparkles className="h-3 w-3" />
            Try these examples:
          </p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map((example) => (
              <button
                key={example}
                onClick={() => handleExampleClick(example)}
                className="text-xs px-3 py-1.5 bg-surface-secondary hover:bg-surface-tertiary text-text-secondary hover:text-text-primary rounded-lg transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
