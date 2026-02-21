"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  User,
  Mail,
  Globe,
  Lock,
  Bell,
  CreditCard,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

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

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  // Form fields
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("en");
  const [timezone, setTimezone] = useState("UTC");

  // Password change
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSaved, setPasswordSaved] = useState(false);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-3xl animate-in">
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-text-secondary">Manage your account settings and preferences.</p>
      </div>

      {/* Profile Section */}
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
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">Language</label>
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
              <label className="block text-sm font-medium text-text-secondary mb-1">Timezone</label>
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

          <div className="flex items-center gap-3 pt-2">
            <Button onClick={handleSaveProfile} disabled={saving}>
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

      {/* Password Section */}
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

          <div className="flex items-center gap-3 pt-2">
            <Button
              onClick={handleChangePassword}
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

      {/* Subscription Section */}
      <Card className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <CreditCard className="h-5 w-5 text-primary-500" />
          <h2 className="text-lg font-display font-semibold text-text-primary">Subscription</h2>
        </div>

        <div className="flex items-center justify-between p-4 bg-surface-secondary rounded-xl">
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
    </div>
  );
}
