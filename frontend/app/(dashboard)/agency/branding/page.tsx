"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Palette, Save, Loader2, CheckCircle, Globe } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { api, parseApiError, AgencyProfile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_COLORS = {
  primary: "#6366f1",
  secondary: "#8b5cf6",
  accent: "#06b6d4",
};

// ---------------------------------------------------------------------------
// ColorSwatch — a paired color input + preview swatch
// ---------------------------------------------------------------------------

interface ColorSwatchProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}

function ColorSwatch({ label, value, onChange, disabled }: ColorSwatchProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="block text-sm font-medium text-text-secondary">{label}</label>
      <div className="flex items-center gap-3">
        {/* Native color picker */}
        <div className="relative">
          <input
            type="color"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className="sr-only"
            id={`color-${label.toLowerCase()}`}
          />
          <label
            htmlFor={`color-${label.toLowerCase()}`}
            className="block h-10 w-10 rounded-xl border-2 border-surface-tertiary cursor-pointer shadow-sm transition-transform hover:scale-105"
            style={{ backgroundColor: value }}
            aria-label={`Pick ${label} color`}
          />
        </div>

        {/* Hex text input */}
        <Input
          value={value}
          onChange={(e) => {
            const v = e.target.value;
            // Allow partial typing; only propagate valid 3- or 6-char hex values
            if (/^#[0-9a-fA-F]{0,6}$/.test(v)) onChange(v);
          }}
          disabled={disabled}
          placeholder="#000000"
          className="font-mono w-32"
          maxLength={7}
        />

        {/* Preview swatch */}
        <div
          className="h-8 w-8 rounded-lg border border-surface-tertiary flex-shrink-0"
          style={{ backgroundColor: value }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="bg-surface-tertiary animate-pulse rounded-2xl h-64" />
      <div className="bg-surface-tertiary animate-pulse rounded-2xl h-52" />
      <div className="bg-surface-tertiary animate-pulse rounded-2xl h-32" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AgencyBrandingPage() {
  const [profile, setProfile] = useState<AgencyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Form fields
  const [agencyName, setAgencyName] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [footerText, setFooterText] = useState("");

  // Brand colors
  const [primaryColor, setPrimaryColor] = useState(DEFAULT_COLORS.primary);
  const [secondaryColor, setSecondaryColor] = useState(DEFAULT_COLORS.secondary);
  const [accentColor, setAccentColor] = useState(DEFAULT_COLORS.accent);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    setLoading(true);
    try {
      const data = await api.agency.getProfile();
      applyProfile(data);
    } catch (err) {
      // 404 means no agency profile has been created yet — blank form is fine
      const is404 = axios.isAxiosError(err) && err.response?.status === 404;
      if (!is404) {
        toast.error(parseApiError(err).message);
      }
    } finally {
      setLoading(false);
    }
  };

  const applyProfile = (data: AgencyProfile) => {
    setProfile(data);
    setAgencyName(data.agency_name ?? "");
    setLogoUrl(data.logo_url ?? "");
    setContactEmail(data.contact_email ?? "");
    setFooterText(data.footer_text ?? "");

    const colors = data.brand_colors ?? {};
    setPrimaryColor(colors.primary ?? DEFAULT_COLORS.primary);
    setSecondaryColor(colors.secondary ?? DEFAULT_COLORS.secondary);
    setAccentColor(colors.accent ?? DEFAULT_COLORS.accent);
  };

  const handleSave = async () => {
    if (!agencyName.trim()) {
      toast.error("Agency name is required.");
      return;
    }

    setSaving(true);
    setSaved(false);

    const payload = {
      agency_name: agencyName.trim(),
      logo_url: logoUrl.trim() || undefined,
      contact_email: contactEmail.trim() || undefined,
      footer_text: footerText.trim() || undefined,
      brand_colors: {
        primary: primaryColor,
        secondary: secondaryColor,
        accent: accentColor,
      },
    };

    try {
      let updated: AgencyProfile;
      if (profile) {
        updated = await api.agency.updateProfile(payload);
      } else {
        updated = await api.agency.createProfile(payload);
      }
      applyProfile(updated);
      setSaved(true);
      toast.success("Branding saved successfully.");
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-in max-w-3xl">
        {/* Back nav skeleton */}
        <div className="bg-surface-tertiary animate-pulse rounded-2xl h-9 w-24" />
        <PageSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in max-w-3xl">
      {/* Back nav */}
      <div className="flex items-center gap-3">
        <Link href="/agency">
          <Button variant="ghost" size="sm" className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Agency
          </Button>
        </Link>
      </div>

      {/* Page title */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">
          Branding &amp; White-Label
        </h1>
        <p className="mt-1 text-text-secondary">
          Customize your agency identity and client-facing appearance.
        </p>
      </div>

      {/* General Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Palette className="h-4 w-4 text-primary-500" />
            Agency Identity
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Agency name */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Agency Name <span className="text-red-500">*</span>
            </label>
            <Input
              value={agencyName}
              onChange={(e) => setAgencyName(e.target.value)}
              placeholder="Acme Marketing Agency"
              disabled={saving}
            />
          </div>

          {/* Logo URL */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Logo URL
            </label>
            <Input
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
              placeholder="https://example.com/logo.png"
              disabled={saving}
            />
            {logoUrl && (
              <div className="mt-2 flex items-center gap-3">
                <img
                  src={logoUrl}
                  alt="Agency logo preview"
                  className="h-10 max-w-[160px] object-contain rounded-lg border border-surface-tertiary bg-surface-secondary p-1"
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).style.display = "none";
                  }}
                />
                <p className="text-xs text-text-muted">Logo preview</p>
              </div>
            )}
          </div>

          {/* Contact email */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Contact Email
            </label>
            <Input
              type="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="hello@youragency.com"
              disabled={saving}
            />
            <p className="mt-1 text-xs text-text-muted">
              Shown on client-facing reports and portal pages.
            </p>
          </div>

          {/* Footer text */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Footer Text
            </label>
            <Input
              value={footerText}
              onChange={(e) => setFooterText(e.target.value)}
              placeholder="Powered by Acme Marketing Agency"
              disabled={saving}
            />
            <p className="mt-1 text-xs text-text-muted">
              Appears at the bottom of generated reports.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Brand Colors */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Palette className="h-4 w-4 text-primary-500" />
            Brand Colors
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <p className="text-sm text-text-secondary">
            These colors are applied to client portal pages and generated reports.
          </p>

          <div className="grid sm:grid-cols-3 gap-6">
            <ColorSwatch
              label="Primary"
              value={primaryColor}
              onChange={setPrimaryColor}
              disabled={saving}
            />
            <ColorSwatch
              label="Secondary"
              value={secondaryColor}
              onChange={setSecondaryColor}
              disabled={saving}
            />
            <ColorSwatch
              label="Accent"
              value={accentColor}
              onChange={setAccentColor}
              disabled={saving}
            />
          </div>

          {/* Live preview strip */}
          <div className="rounded-xl overflow-hidden border border-surface-tertiary">
            <div
              className="h-3"
              style={{ backgroundColor: primaryColor }}
              aria-hidden="true"
            />
            <div className="flex gap-0">
              <div
                className="h-2 flex-1"
                style={{ backgroundColor: secondaryColor }}
                aria-hidden="true"
              />
              <div
                className="h-2 flex-1"
                style={{ backgroundColor: accentColor }}
                aria-hidden="true"
              />
            </div>
          </div>
          <p className="text-xs text-text-muted">Color preview strip</p>
        </CardContent>
      </Card>

      {/* Custom Domain */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4 text-primary-500" />
            Custom Domain
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Custom Domain
            </label>
            <Input
              value={profile?.custom_domain ?? ""}
              readOnly
              disabled
              placeholder="reports.youragency.com"
              className="bg-surface-secondary cursor-not-allowed"
            />
          </div>
          <p className="text-sm text-text-muted flex items-start gap-2">
            <span className="mt-0.5 inline-block h-4 w-4 flex-shrink-0 rounded-full bg-amber-100 text-amber-600 text-center text-xs leading-4">
              i
            </span>
            Contact support to configure a custom domain for your client portal. DNS propagation
            may take up to 48 hours after setup.
          </p>
        </CardContent>
      </Card>

      {/* Save */}
      <div className="flex items-center gap-3 pb-6">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          {saving ? "Saving..." : "Save Branding"}
        </Button>

        {saved && (
          <span className="flex items-center gap-1.5 text-sm text-green-600">
            <CheckCircle className="h-4 w-4" />
            Saved
          </span>
        )}
      </div>
    </div>
  );
}
