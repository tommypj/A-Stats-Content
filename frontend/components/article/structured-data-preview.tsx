"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Code2, Copy, CheckCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { clsx } from "clsx";

interface StructuredDataPreviewProps {
  schemas: Record<string, unknown> | null | undefined;
}

const TAB_LABELS: Record<string, string> = {
  article: "Article",
  faq: "FAQ",
};

export function StructuredDataPreview({ schemas }: StructuredDataPreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  if (!schemas || Object.keys(schemas).length === 0) return null;

  const schemaKeys = Object.keys(schemas);
  const currentTab = activeTab ?? schemaKeys[0] ?? null;
  const activeSchema = currentTab ? (schemas[currentTab] as Record<string, unknown> | undefined) : undefined;

  const formattedJson = activeSchema ? JSON.stringify(activeSchema, null, 2) : "";
  const scriptTag = activeSchema
    ? `<script type="application/ld+json">\n${formattedJson}\n</script>`
    : "";

  const schemaType = activeSchema?.["@type"];

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(scriptTag);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback silent
    }
  };

  return (
    <Card className="p-4">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-text-secondary" />
          <span className="font-medium text-text-primary text-sm">Structured Data</span>
          <span className="text-xs text-text-muted bg-surface-secondary px-1.5 py-0.5 rounded-full">
            {schemaKeys.length} {schemaKeys.length === 1 ? "schema" : "schemas"}
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-text-muted" />
        ) : (
          <ChevronDown className="h-4 w-4 text-text-muted" />
        )}
      </button>

      {expanded ? (
        <div className="mt-3 space-y-3">
          {/* Tabs */}
          {schemaKeys.length > 1 ? (
            <div className="flex gap-1">
              {schemaKeys.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setActiveTab(key)}
                  className={clsx(
                    "px-2.5 py-1 rounded-md text-xs font-medium transition-colors",
                    currentTab === key
                      ? "bg-primary-100 text-primary-700"
                      : "bg-surface-secondary text-text-secondary hover:text-text-primary"
                  )}
                >
                  {TAB_LABELS[key] || key}
                </button>
              ))}
            </div>
          ) : null}

          {/* Schema type label */}
          {schemaType ? (
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <span className="px-1.5 py-0.5 bg-surface-secondary rounded font-mono">
                @type: {String(schemaType)}
              </span>
            </div>
          ) : null}

          {/* JSON preview */}
          <div className="relative">
            <pre className="bg-surface-secondary rounded-lg p-3 text-xs font-mono text-text-secondary overflow-x-auto max-h-64 overflow-y-auto">
              {formattedJson}
            </pre>
            <button
              type="button"
              onClick={handleCopy}
              className="absolute top-2 right-2 p-1.5 rounded-md bg-surface hover:bg-surface-tertiary transition-colors"
              title="Copy as <script> tag"
            >
              {copied ? (
                <CheckCircle className="h-3.5 w-3.5 text-green-600" />
              ) : (
                <Copy className="h-3.5 w-3.5 text-text-muted" />
              )}
            </button>
          </div>

          <p className="text-xs text-text-muted">
            Copy and paste into your page&apos;s {`<head>`} for rich search results.
          </p>
        </div>
      ) : null}
    </Card>
  );
}
