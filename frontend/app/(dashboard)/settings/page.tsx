"use client";

import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import { api, getImageUrl, parseApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  User,
  Lock,
  CreditCard,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
  Trash2,
  Upload,
  Download,
  Camera,
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
  avatar_url?: string;
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
  onAvatarChange: (file: File) => void;
  avatarUploading: boolean;
  isDirty: boolean;
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
  onAvatarChange,
  avatarUploading,
  isDirty,
}: ProfileSectionProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const avatarUrl = profile?.avatar_url ? getImageUrl(profile.avatar_url) : null;
  const initials = (profile?.name || profile?.email || "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <Card className="p-6">
      <div className="flex items-center gap-3 mb-6">
        <User className="h-5 w-5 text-primary-500" />
        <h2 className="text-lg font-display font-semibold text-text-primary">Profile</h2>
      </div>

      <div className="space-y-4">
        {/* Avatar */}
        <div className="flex items-center gap-4">
          <div className="relative group">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={`${profile?.name || "User"}'s profile photo`}
                className="h-16 w-16 rounded-full object-cover border-2 border-surface-tertiary"
              />
            ) : (
              <div className="h-16 w-16 rounded-full bg-primary-100 flex items-center justify-center border-2 border-surface-tertiary">
                <span className="text-lg font-semibold text-primary-600">{initials}</span>
              </div>
            )}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={avatarUploading}
              className="absolute inset-0 rounded-full bg-black/0 group-hover:bg-black/40 flex items-center justify-center transition-colors cursor-pointer"
              aria-label="Change avatar"
            >
              {avatarUploading ? (
                <Loader2 className="h-5 w-5 text-white animate-spin opacity-0 group-hover:opacity-100 transition-opacity" />
              ) : (
                <Camera className="h-5 w-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              )}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onAvatarChange(file);
                e.target.value = "";
              }}
            />
          </div>
          <div>
            <p className="text-sm font-medium text-text-primary">Profile Photo</p>
            <p className="text-xs text-text-muted">JPEG, PNG or WebP. Max 2 MB.</p>
          </div>
        </div>

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
          {isDirty && !saved && (
            <span className="flex items-center gap-1 text-sm text-amber-600">
              <AlertCircle className="h-4 w-4" /> Unsaved changes
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
        <Link href="/settings/billing">
          <Button variant="outline">
            Manage Plan
          </Button>
        </Link>
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
// DeleteAccountDialog
// A self-contained modal that requires the user to type a confirmation phrase
// before the delete button becomes active.
// ---------------------------------------------------------------------------

const DELETE_PHRASE = "DELETE MY ACCOUNT";

interface DeleteAccountDialogProps {
  isOpen: boolean;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

function DeleteAccountDialog({
  isOpen,
  isDeleting,
  onClose,
  onConfirm,
}: DeleteAccountDialogProps) {
  const [typed, setTyped] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  // Reset typed value whenever dialog opens/closes
  useEffect(() => {
    if (!isOpen) {
      setTyped("");
    }
  }, [isOpen]);

  // Focus the input when opened; handle Escape + focus trap
  useEffect(() => {
    if (!isOpen) return;

    const frame = requestAnimationFrame(() => {
      inputRef.current?.focus();
    });

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isDeleting) {
        onClose();
        return;
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(
          dialogRef.current.querySelectorAll<HTMLElement>(
            "button:not([disabled]), input:not([disabled])"
          )
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, isDeleting, onClose]);

  if (!isOpen) return null;

  const confirmed = typed === DELETE_PHRASE;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        onClick={() => {
          if (!isDeleting) onClose();
        }}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-account-title"
          className="bg-surface rounded-2xl border border-red-200 shadow-lg max-w-md w-full p-6 space-y-4"
        >
          {/* Icon + Title */}
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-red-50">
              <Trash2 className="h-5 w-5 text-red-500" />
            </div>
            <div>
              <h3
                id="delete-account-title"
                className="text-lg font-display font-semibold text-text-primary"
              >
                Delete Account
              </h3>
              <p className="mt-1 text-sm text-text-secondary">
                This action is{" "}
                <span className="font-semibold text-red-600">permanent and irreversible</span>.
                All your articles, outlines, images, projects, and integrations will be deleted
                immediately. There is no undo.
              </p>
            </div>
          </div>

          {/* Confirmation input */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Type{" "}
              <span className="font-mono font-semibold text-red-600">{DELETE_PHRASE}</span> to
              confirm
            </label>
            <Input
              ref={inputRef}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder={DELETE_PHRASE}
              disabled={isDeleting}
              className="font-mono"
              autoComplete="off"
              spellCheck={false}
            />
          </div>

          {/* Buttons */}
          <div className="flex justify-end gap-3 pt-1">
            <button onClick={onClose} disabled={isDeleting} className="btn-secondary">
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={!confirmed || isDeleting}
              className="px-4 py-2 rounded-xl text-sm font-medium text-white transition-colors bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDeleting ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Deleting...
                </span>
              ) : (
                "Delete My Account"
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// DangerZoneSection
// ---------------------------------------------------------------------------

interface DangerZoneSectionProps {
  onDeleteAccount: () => void;
  onExportData: () => void;
  exporting: boolean;
}

function DangerZoneSection({ onDeleteAccount, onExportData, exporting }: DangerZoneSectionProps) {
  return (
    <Card className="p-6 border-red-200">
      <div className="flex items-center gap-3 mb-4">
        <Trash2 className="h-5 w-5 text-red-500" />
        <h2 className="text-lg font-display font-semibold text-red-600">Danger Zone</h2>
      </div>

      <div className="space-y-4">
        {/* Export data */}
        <div className="rounded-xl border border-surface-tertiary p-4 bg-surface-secondary space-y-3">
          <div>
            <p className="font-medium text-text-primary">Export my data</p>
            <p className="text-sm text-text-secondary mt-1">
              Download a JSON file containing all your account data including articles, outlines,
              images, knowledge sources, and social posts.
            </p>
          </div>
          <Button variant="outline" onClick={onExportData} disabled={exporting}>
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Download className="h-4 w-4 mr-2" />
            )}
            {exporting ? "Exporting..." : "Export My Data"}
          </Button>
        </div>

        {/* Delete account */}
        <div className="rounded-xl border border-red-200 p-4 bg-red-50 space-y-3">
          <div>
            <p className="font-medium text-text-primary">Delete your account</p>
            <p className="text-sm text-text-secondary mt-1">
              Permanently delete your account and all associated data including articles, outlines,
              images, and project memberships. This cannot be undone.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={onDeleteAccount}
            className="text-red-600 border-red-300 hover:bg-red-100 hover:border-red-400"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete My Account
          </Button>
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
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<TabId>(getInitialTab);

  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const passwordSavedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
      if (passwordSavedTimerRef.current) clearTimeout(passwordSavedTimerRef.current);
    };
  }, []);

  // Profile fields
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en");
  const [timezone, setTimezone] = useState("UTC");

  // Original profile values (for dirty tracking)
  const [originalName, setOriginalName] = useState("");
  const [originalLanguage, setOriginalLanguage] = useState("en");
  const [originalTimezone, setOriginalTimezone] = useState("UTC");

  const isDirty =
    name !== originalName || language !== originalLanguage || timezone !== originalTimezone;

  // Password change
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSaved, setPasswordSaved] = useState(false);

  // Avatar upload
  const [avatarUploading, setAvatarUploading] = useState(false);

  // Data export
  const [exporting, setExporting] = useState(false);

  // Account deletion
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Warn before leaving with unsaved changes
  useEffect(() => {
    if (!isDirty) return;
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  // Sync hash when tab changes
  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    window.location.hash = tab;
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await api.auth.me();
      setProfile(data);
      setName(data.name);
      setLanguage(data.language || "en");
      setTimezone(data.timezone || "UTC");
      setOriginalName(data.name);
      setOriginalLanguage(data.language || "en");
      setOriginalTimezone(data.timezone || "UTC");
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
      setOriginalName(name);
      setOriginalLanguage(language);
      setOriginalTimezone(timezone);
      setSaved(true);
      savedTimerRef.current = setTimeout(() => setSaved(false), 3000);
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
      passwordSavedTimerRef.current = setTimeout(() => setPasswordSaved(false), 3000);
    } catch (err) {
      const apiError = parseApiError(err);
      setPasswordError(apiError.message || "Current password is incorrect");
    }
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await api.auth.deleteAccount();
      // Clear auth tokens and redirect to login
      localStorage.removeItem("auth_token");
      localStorage.removeItem("refresh_token");
      toast.success("Your account has been deleted.");
      router.push("/login");
    } catch {
      toast.error("Failed to delete account. Please try again.");
      setIsDeleting(false);
    }
  };

  const handleAvatarChange = async (file: File) => {
    setAvatarUploading(true);
    try {
      const updated = await api.auth.uploadAvatar(file);
      setProfile((prev) => (prev ? { ...prev, avatar_url: updated.avatar_url } : prev));
      toast.success("Avatar updated successfully.");
    } catch {
      toast.error("Failed to upload avatar. Please try again.");
    } finally {
      setAvatarUploading(false);
    }
  };

  const handleExportData = async () => {
    setExporting(true);
    try {
      await api.auth.exportData();
      toast.success("Data export downloaded.");
    } catch {
      toast.error("Failed to export data. Please try again.");
    } finally {
      setExporting(false);
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
        <div className="space-y-6">
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
            onAvatarChange={handleAvatarChange}
            avatarUploading={avatarUploading}
            isDirty={isDirty}
          />

          <DangerZoneSection
            onDeleteAccount={() => setShowDeleteDialog(true)}
            onExportData={handleExportData}
            exporting={exporting}
          />
        </div>
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

      {activeTab === "billing" && <BillingSection profile={profile} />}

      {/* Account deletion confirmation dialog */}
      <DeleteAccountDialog
        isOpen={showDeleteDialog}
        isDeleting={isDeleting}
        onClose={() => setShowDeleteDialog(false)}
        onConfirm={handleDeleteAccount}
      />
    </div>
  );
}
