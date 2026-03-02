"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Camera } from "lucide-react";
import { toast } from "sonner";

import { api, parseApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth";
import { useRequireAuth } from "@/lib/auth";

const profileSchema = z.object({
  name: z.string().min(1).max(255),
  email: z.string().email(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

export default function ProfileSettingsPage() {
  const t = useTranslations("settings.profile");
  const { isAuthenticated, isLoading: authLoading } = useRequireAuth();
  const { user, setUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

  // Email change form state
  const [showEmailChangeForm, setShowEmailChangeForm] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [emailChangePassword, setEmailChangePassword] = useState("");
  const [emailChangeSending, setEmailChangeSending] = useState(false);
  const [emailChangeSent, setEmailChangeSent] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: user?.name || "",
      email: user?.email || "",
    },
  });

  if (authLoading) return null;
  if (!isAuthenticated) return null;

  const onSubmit = async (data: ProfileFormData) => {
    setIsLoading(true);
    try {
      await api.auth.updateProfile({ name: data.name });

      if (user) {
        setUser({ ...user, name: data.name });
      }

      toast.success("Profile updated successfully");
    } catch (error) {
      toast.error(parseApiError(error).message || "Failed to update profile");
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmailChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailChangeSending(true);
    try {
      await api.auth.changeEmail(newEmail, emailChangePassword);
      setEmailChangeSent(true);
      setEmailChangePassword("");
    } catch (err) {
      toast.error(parseApiError(err).message);
    } finally {
      setEmailChangeSending(false);
    }
  };

  return (
    <div className="card">
      <div className="p-6 border-b border-surface-tertiary">
        <h2 className="font-display text-lg font-semibold text-text-primary">
          {t("title")}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">{t("description")}</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
        {/* Avatar */}
        <div className="flex items-center gap-6">
          <div className="relative">
            <div className="h-20 w-20 rounded-full bg-healing-lavender flex items-center justify-center">
              <span className="text-2xl font-medium text-text-primary">
                {user?.name?.charAt(0).toUpperCase() || "U"}
              </span>
            </div>
            <button
              type="button"
              className="absolute bottom-0 right-0 h-8 w-8 rounded-full bg-primary-500 text-white flex items-center justify-center hover:bg-primary-600 transition-colors"
            >
              <Camera className="h-4 w-4" />
            </button>
          </div>
          <div>
            <p className="text-sm font-medium text-text-primary">{t("avatar")}</p>
            <button
              type="button"
              className="mt-1 text-sm text-primary-500 hover:text-primary-600"
            >
              {t("changeAvatar")}
            </button>
          </div>
        </div>

        {/* Name */}
        <Input
          label={t("name")}
          error={errors.name?.message}
          {...register("name")}
        />

        {/* Email (read-only) */}
        <Input
          label={t("email")}
          type="email"
          disabled
          helperText="Email cannot be changed here"
          {...register("email")}
        />

        {/* Submit */}
        <div className="flex justify-end pt-4">
          <Button type="submit" disabled={!isDirty || isLoading} isLoading={isLoading}>
            {t("save")}
          </Button>
        </div>
      </form>

      {/* Email change — kept outside the profile form to avoid nested <form> elements */}
      <div className="px-6 pb-6 border-t border-surface-tertiary pt-6">
        <h4 className="text-sm font-medium text-text-primary mb-4">Change Email Address</h4>
        {!showEmailChangeForm ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setShowEmailChangeForm(true);
              setEmailChangeSent(false);
            }}
          >
            Change email
          </Button>
        ) : (
          <form onSubmit={handleEmailChange} className="space-y-3 max-w-sm">
            <Input
              label="New email address"
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              required
              autoComplete="email"
            />
            <Input
              label="Current password"
              type="password"
              value={emailChangePassword}
              onChange={(e) => setEmailChangePassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            <div className="flex gap-2">
              <Button type="submit" size="sm" isLoading={emailChangeSending}>
                Send verification
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowEmailChangeForm(false);
                  setEmailChangeSent(false);
                  setNewEmail("");
                  setEmailChangePassword("");
                }}
              >
                Cancel
              </Button>
            </div>
            {emailChangeSent && (
              <p className="text-sm text-green-600">
                Verification email sent! Check your new inbox.
              </p>
            )}
          </form>
        )}
      </div>
    </div>
  );
}
