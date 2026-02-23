"use client";

import { useEffect, useState } from "react";
import { clsx } from "clsx";
import { api, parseApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  User,
  Globe,
  Lock,
  CreditCard,
  Plug,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
  ExternalLink,
  Search,
  Unplug,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UserProfile {
  id: string;
  email: string;
  name: string;
  language: string;
  timezone: string;
  subscription_tier: string;
  subscription_status: string;
  email_verified: boolean;
  articles_generated_this_month: number;
  outlines_generated_this_month: number;
  images_generated_this_month: number;
}

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "password", label: "Password", icon: Lock },
  { id: "integrations", label: "Integrations", icon: Plug },
  { id: "billing", label: "Billing", icon: CreditCard },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ---------------------------------------------------------------------------
// ProfileSection
// ---------------------------------------------------------------------------

interface ProfileSectionProps {
  profile: UserProfile | null;
  name: string;
  setName: (v: string) => void;
  language: string;
  setLanguage: (v: string) => void;
  timezone: string;
  setTimezone: (v: string) => void;
  saving: boolean;
  saved: boolean;
  error: string;
  onSave: () => void;
}

function ProfileSection({
  profile,
  name,
  setName,
  language,
  setLanguage,
  timezone,
  setTimezone,
  saving,
  saved,
  error,
  onSave,
}: ProfileSectionProps) {
  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <User className="h-5 w-5 text-primary-500" />
        <h2 className="text-lg font-display font-semibold text-text-primary">Profile</h2>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">Email</label>
          <div className="flex items-center gap-2">
            <Input value={profile?.email || ""} disabled className="bg-surface-secondary" />
            {profile?.email_verified ? (
              <span className="flex items-center gap-1 text-xs text-green-600">
                <CheckCircle className="h-3.5 w-3.5" /> Verified
              </span>
            ) : (
              <span className="flex items-center gap-1 text-xs text-amber-600">
                <AlertCircle className="h-3.5 w-3.5" /> Not verified
              </span>
            )}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">Name</label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name"
          />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full rounded-xl border border-surface-tertiary bg-white px-3 py-2 text-sm"
            >
              <option value="en">English</option>
              <option value="ro">Romanian</option>
              <option value="es">Spanish</option>
              <option value="de">German</option>
              <option value="fr">French</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Timezone
            </label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full rounded-xl border border-surface-tertiary bg-white px-3 py-2 text-sm"
            >
              <option value="UTC">UTC</option>
              <option value="Europe/Bucharest">Europe/Bucharest</option>
              <option value="Europe/London">Europe/London</option>
              <option value="America/New_York">America/New York</option>
              <option value="America/Los_Angeles">America/Los Angeles</option>
              <option value="Asia/Tokyo">Asia/Tokyo</option>
            </select>
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button onClick={onSave} disabled={saving}>
            {saving ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Save className="h-4 w-4 mr-2" />
            )}
            Save Changes
          </Button>
          {saved && (
            <span className="flex items-center gap-1 text-sm text-green-600">
              <CheckCircle className="h-4 w-4" /> Saved
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// PasswordSection
// ---------------------------------------------------------------------------

interface PasswordSectionProps {
  currentPassword: string;
  setCurrentPassword: (v: string) => void;
  newPassword: string;
  setNewPassword: (v: string) => void;
  confirmPassword: string;
  setConfirmPassword: (v: string) => void;
  passwordError: string;
  passwordSaved: boolean;
  onChangePassword: () => void;
}

function PasswordSection({
  currentPassword,
  setCurrentPassword,
  newPassword,
  setNewPassword,
  confirmPassword,
  setConfirmPassword,
  passwordError,
  passwordSaved,
  onChangePassword,
}: PasswordSectionProps) {
  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <Lock className="h-5 w-5 text-primary-500" />
        <h2 className="text-lg font-display font-semibold text-text-primary">Change Password</h2>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            Current Password
          </label>
          <Input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Enter current password"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            New Password
          </label>
          <Input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Enter new password"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">
            Confirm New Password
          </label>
          <Input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
          />
        </div>

        {passwordError && <p className="text-sm text-red-600">{passwordError}</p>}

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button
            onClick={onChangePassword}
            disabled={!currentPassword || !newPassword || !confirmPassword}
            variant="outline"
          >
            Update Password
          </Button>
          {passwordSaved && (
            <span className="flex items-center gap-1 text-sm text-green-600">
              <CheckCircle className="h-4 w-4" /> Password updated
            </span>
          )}
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// IntegrationsSection
// ---------------------------------------------------------------------------

interface IntegrationsSectionProps {
  // WordPress
  wpConnected: boolean;
  wpSiteUrl: string;
  wpUsername: string;
  wpSiteName: string;
  wpLoadingStatus: boolean;
  showWpForm: boolean;
  setShowWpForm: (v: boolean) => void;
  wpFormSiteUrl: string;
  setWpFormSiteUrl: (v: string) => void;
  wpFormUsername: string;
  setWpFormUsername: (v: string) => void;
  wpFormAppPassword: string;
  setWpFormAppPassword: (v: string) => void;
  wpConnecting: boolean;
  wpDisconnecting: boolean;
  wpError: string;
  setWpError: (v: string) => void;
  onWpConnect: () => void;
  onWpDisconnect: () => void;
  // GSC
  gscConnected: boolean;
  gscSiteUrl: string;
  gscLastSync: string;
  gscLoadingStatus: boolean;
  gscConnecting: boolean;
  gscDisconnecting: boolean;
  gscError: string;
  onGscConnect: () => void;
  onGscDisconnect: () => void;
}

function IntegrationsSection({
  wpConnected,
  wpSiteUrl,
  wpUsername,
  wpSiteName,
  wpLoadingStatus,
  showWpForm,
  setShowWpForm,
  wpFormSiteUrl,
  setWpFormSiteUrl,
  wpFormUsername,
  setWpFormUsername,
  wpFormAppPassword,
  setWpFormAppPassword,
  wpConnecting,
  wpDisconnecting,
  wpError,
  setWpError,
  onWpConnect,
  onWpDisconnect,
  gscConnected,
  gscSiteUrl,
  gscLastSync,
  gscLoadingStatus,
  gscConnecting,
  gscDisconnecting,
  gscError,
  onGscConnect,
  onGscDisconnect,
}: IntegrationsSectionProps) {
  return (
    <div className="space-y-6">
      {/* WordPress Integration */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Globe className="h-5 w-5 text-primary-500" />
          <h2 className="text-lg font-display font-semibold text-text-primary">WordPress</h2>
        </div>

        {wpLoadingStatus ? (
          <div className="flex items-center gap-2 text-text-secondary">
            <Loader2 className="h-4 w-4 animate-spin" /> Checking connection...
          </div>
        ) : wpConnected ? (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-xl space-y-1">
              <p className="flex items-center gap-2 text-sm font-medium text-green-800">
                <CheckCircle className="h-4 w-4" /> Connected
              </p>
              {wpSiteName && (
                <p className="text-sm text-green-700">Site: {wpSiteName}</p>
              )}
              <p className="text-sm text-green-700">URL: {wpSiteUrl}</p>
              <p className="text-sm text-green-700">Username: {wpUsername}</p>
            </div>
            <Button
              variant="outline"
              onClick={onWpDisconnect}
              disabled={wpDisconnecting}
              className="text-red-600 border-red-200 hover:bg-red-50"
            >
              {wpDisconnecting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Unplug className="h-4 w-4 mr-2" />
              )}
              Disconnect
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-text-secondary">
              Connect your WordPress site to publish articles directly from the dashboard.
            </p>

            {!showWpForm ? (
              <Button onClick={() => setShowWpForm(true)}>
                <ExternalLink className="h-4 w-4 mr-2" />
                Connect WordPress
              </Button>
            ) : (
              <div className="space-y-3 p-4 bg-surface-secondary rounded-xl">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Site URL
                  </label>
                  <Input
                    value={wpFormSiteUrl}
                    onChange={(e) => setWpFormSiteUrl(e.target.value)}
                    placeholder="https://yoursite.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Username
                  </label>
                  <Input
                    value={wpFormUsername}
                    onChange={(e) => setWpFormUsername(e.target.value)}
                    placeholder="WordPress username"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1">
                    Application Password
                  </label>
                  <Input
                    type="password"
                    value={wpFormAppPassword}
                    onChange={(e) => setWpFormAppPassword(e.target.value)}
                    placeholder="xxxx xxxx xxxx xxxx xxxx xxxx"
                  />
                  <p className="mt-1 text-xs text-text-muted">
                    Generate one in WordPress &rarr; Users &rarr; Profile &rarr; Application
                    Passwords
                  </p>
                </div>

                {wpError && <p className="text-sm text-red-600">{wpError}</p>}

                <div className="flex flex-wrap gap-2 pt-1">
                  <Button onClick={onWpConnect} disabled={wpConnecting}>
                    {wpConnecting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                    Connect
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowWpForm(false);
                      setWpError("");
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Google Search Console Integration */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <Search className="h-5 w-5 text-primary-500" />
          <h2 className="text-lg font-display font-semibold text-text-primary">
            Google Search Console
          </h2>
        </div>

        {gscLoadingStatus ? (
          <div className="flex items-center gap-2 text-text-secondary">
            <Loader2 className="h-4 w-4 animate-spin" /> Checking connection...
          </div>
        ) : gscConnected ? (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-xl space-y-1">
              <p className="flex items-center gap-2 text-sm font-medium text-green-800">
                <CheckCircle className="h-4 w-4" /> Connected
              </p>
              {gscSiteUrl && (
                <p className="text-sm text-green-700">Site: {gscSiteUrl}</p>
              )}
              {gscLastSync && (
                <p className="text-sm text-green-700">
                  Last sync: {new Date(gscLastSync).toLocaleDateString()}
                </p>
              )}
            </div>
            <Button
              variant="outline"
              onClick={onGscDisconnect}
              disabled={gscDisconnecting}
              className="text-red-600 border-red-200 hover:bg-red-50"
            >
              {gscDisconnecting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Unplug className="h-4 w-4 mr-2" />
              )}
              Disconnect
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-text-secondary">
              Connect Google Search Console to track your search performance and get keyword
              insights.
            </p>

            {gscError && <p className="text-sm text-red-600">{gscError}</p>}

            <Button onClick={onGscConnect} disabled={gscConnecting}>
              {gscConnecting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <ExternalLink className="h-4 w-4 mr-2" />
              )}
              Connect Google Search Console
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BillingSection
// ---------------------------------------------------------------------------

interface BillingSectionProps {
  profile: UserProfile | null;
}

function BillingSection({ profile }: BillingSectionProps) {
  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <CreditCard className="h-5 w-5 text-primary-500" />
        <h2 className="text-lg font-display font-semibold text-text-primary">Subscription</h2>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 bg-surface-secondary rounded-xl">
        <div>
          <p className="font-medium text-text-primary capitalize">
            {profile?.subscription_tier || "Free"} Plan
          </p>
          <p className="text-sm text-text-secondary capitalize">
            Status: {profile?.subscription_status || "Active"}
          </p>
        </div>
        <Button variant="outline" onClick={() => (window.location.href = "/settings/billing")}>
          Manage Plan
        </Button>
      </div>

      <div className="mt-4 grid sm:grid-cols-3 gap-4">
        <div className="text-center p-3 bg-surface-secondary rounded-xl">
          <p className="text-2xl font-bold text-text-primary">
            {profile?.articles_generated_this_month || 0}
          </p>
          <p className="text-xs text-text-muted">Articles This Month</p>
        </div>
        <div className="text-center p-3 bg-surface-secondary rounded-xl">
          <p className="text-2xl font-bold text-text-primary">
            {profile?.outlines_generated_this_month || 0}
          </p>
          <p className="text-xs text-text-muted">Outlines This Month</p>
        </div>
        <div className="text-center p-3 bg-surface-secondary rounded-xl">
          <p className="text-2xl font-bold text-text-primary">
            {profile?.images_generated_this_month || 0}
          </p>
          <p className="text-xs text-text-muted">Images This Month</p>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

function getInitialTab(): TabId {
  if (typeof window === "undefined") return "profile";
  const hash = window.location.hash.replace("#", "") as TabId;
  return TABS.some((t) => t.id === hash) ? hash : "profile";
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab);

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  // Profile fields
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en");
  const [timezone, setTimezone] = useState("UTC");

  // Password change
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSaved, setPasswordSaved] = useState(false);

  // WordPress integration
  const [wpConnected, setWpConnected] = useState(false);
  const [wpSiteUrl, setWpSiteUrl] = useState("");
  const [wpUsername, setWpUsername] = useState("");
  const [wpSiteName, setWpSiteName] = useState("");
  const [wpLoadingStatus, setWpLoadingStatus] = useState(true);
  const [showWpForm, setShowWpForm] = useState(false);
  const [wpFormSiteUrl, setWpFormSiteUrl] = useState("");
  const [wpFormUsername, setWpFormUsername] = useState("");
  const [wpFormAppPassword, setWpFormAppPassword] = useState("");
  const [wpConnecting, setWpConnecting] = useState(false);
  const [wpDisconnecting, setWpDisconnecting] = useState(false);
  const [wpError, setWpError] = useState("");

  // GSC integration
  const [gscConnected, setGscConnected] = useState(false);
  const [gscSiteUrl, setGscSiteUrl] = useState("");
  const [gscLastSync, setGscLastSync] = useState("");
  const [gscLoadingStatus, setGscLoadingStatus] = useState(true);
  const [gscConnecting, setGscConnecting] = useState(false);
  const [gscDisconnecting, setGscDisconnecting] = useState(false);
  const [gscError, setGscError] = useState("");

  // Sync hash when tab changes
  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    window.location.hash = tab;
  };

  useEffect(() => {
    loadProfile();
    loadWordPressStatus();
    loadGscStatus();
  }, []);

  // Re-check GSC status when window regains focus (after OAuth redirect)
  useEffect(() => {
    const onFocus = () => {
      if (!gscConnected) {
        loadGscStatus();
      }
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [gscConnected]);

  const loadProfile = async () => {
    try {
      const data = await api.auth.me();
      setProfile(data);
      setName(data.name);
      setLanguage(data.language || "en");
      setTimezone(data.timezone || "UTC");
    } catch {
      setError("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    setSaved(false);
    setError("");
    try {
      await api.auth.updateProfile({ name, language, timezone });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      setError("Failed to save profile");
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async () => {
    setPasswordError("");
    setPasswordSaved(false);

    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters");
      return;
    }

    try {
      await api.auth.changePassword(currentPassword, newPassword);
      setPasswordSaved(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setPasswordSaved(false), 3000);
    } catch {
      setPasswordError("Current password is incorrect");
    }
  };

  const loadWordPressStatus = async () => {
    try {
      const status = await api.wordpress.status();
      setWpConnected(status.is_connected);
      setWpSiteUrl(status.site_url || "");
      setWpUsername(status.username || "");
      setWpSiteName(status.site_name || "");
    } catch {
      // 404 means not connected
      setWpConnected(false);
    } finally {
      setWpLoadingStatus(false);
    }
  };

  const handleWpConnect = async () => {
    setWpError("");
    if (!wpFormSiteUrl || !wpFormUsername || !wpFormAppPassword) {
      setWpError("All fields are required");
      return;
    }
    setWpConnecting(true);
    try {
      await api.wordpress.connect({
        site_url: wpFormSiteUrl,
        username: wpFormUsername,
        app_password: wpFormAppPassword,
      });
      setShowWpForm(false);
      setWpFormSiteUrl("");
      setWpFormUsername("");
      setWpFormAppPassword("");
      await loadWordPressStatus();
    } catch (err) {
      setWpError(parseApiError(err).message);
    } finally {
      setWpConnecting(false);
    }
  };

  const handleWpDisconnect = async () => {
    setWpDisconnecting(true);
    try {
      await api.wordpress.disconnect();
      setWpConnected(false);
      setWpSiteUrl("");
      setWpUsername("");
      setWpSiteName("");
    } catch (err) {
      setWpError(parseApiError(err).message);
    } finally {
      setWpDisconnecting(false);
    }
  };

  const loadGscStatus = async () => {
    try {
      const status = await api.analytics.status();
      setGscConnected(status.connected);
      setGscSiteUrl(status.site_url || "");
      setGscLastSync(status.last_sync || "");
    } catch {
      setGscConnected(false);
    } finally {
      setGscLoadingStatus(false);
    }
  };

  const handleGscConnect = async () => {
    setGscError("");
    setGscConnecting(true);
    try {
      const { auth_url } = await api.analytics.getAuthUrl();
      window.open(auth_url, "_blank");
    } catch (err) {
      setGscError(parseApiError(err).message);
    } finally {
      setGscConnecting(false);
    }
  };

  const handleGscDisconnect = async () => {
    setGscDisconnecting(true);
    try {
      await api.analytics.disconnect();
      setGscConnected(false);
      setGscSiteUrl("");
      setGscLastSync("");
    } catch (err) {
      setGscError(parseApiError(err).message);
    } finally {
      setGscDisconnecting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-text-secondary">Manage your account settings and preferences.</p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 p-1 bg-surface-secondary rounded-xl">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            )}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Active section */}
      {activeTab === "profile" && (
        <ProfileSection
          profile={profile}
          name={name}
          setName={setName}
          language={language}
          setLanguage={setLanguage}
          timezone={timezone}
          setTimezone={setTimezone}
          saving={saving}
          saved={saved}
          error={error}
          onSave={handleSaveProfile}
        />
      )}

      {activeTab === "password" && (
        <PasswordSection
          currentPassword={currentPassword}
          setCurrentPassword={setCurrentPassword}
          newPassword={newPassword}
          setNewPassword={setNewPassword}
          confirmPassword={confirmPassword}
          setConfirmPassword={setConfirmPassword}
          passwordError={passwordError}
          passwordSaved={passwordSaved}
          onChangePassword={handleChangePassword}
        />
      )}

      {activeTab === "integrations" && (
        <IntegrationsSection
          wpConnected={wpConnected}
          wpSiteUrl={wpSiteUrl}
          wpUsername={wpUsername}
          wpSiteName={wpSiteName}
          wpLoadingStatus={wpLoadingStatus}
          showWpForm={showWpForm}
          setShowWpForm={setShowWpForm}
          wpFormSiteUrl={wpFormSiteUrl}
          setWpFormSiteUrl={setWpFormSiteUrl}
          wpFormUsername={wpFormUsername}
          setWpFormUsername={setWpFormUsername}
          wpFormAppPassword={wpFormAppPassword}
          setWpFormAppPassword={setWpFormAppPassword}
          wpConnecting={wpConnecting}
          wpDisconnecting={wpDisconnecting}
          wpError={wpError}
          setWpError={setWpError}
          onWpConnect={handleWpConnect}
          onWpDisconnect={handleWpDisconnect}
          gscConnected={gscConnected}
          gscSiteUrl={gscSiteUrl}
          gscLastSync={gscLastSync}
          gscLoadingStatus={gscLoadingStatus}
          gscConnecting={gscConnecting}
          gscDisconnecting={gscDisconnecting}
          gscError={gscError}
          onGscConnect={handleGscConnect}
          onGscDisconnect={handleGscDisconnect}
        />
      )}

      {activeTab === "billing" && <BillingSection profile={profile} />}
    </div>
  );
}
