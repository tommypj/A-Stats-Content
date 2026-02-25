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

const profileSchema = z.object({
  name: z.string().min(1).max(255),
  email: z.string().email(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

export default function ProfileSettingsPage() {
  const t = useTranslations("settings.profile");
  const { user, setUser } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

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
          helperText="Email cannot be changed"
          {...register("email")}
        />

        {/* Submit */}
        <div className="flex justify-end pt-4">
          <Button type="submit" disabled={!isDirty || isLoading} isLoading={isLoading}>
            {t("save")}
          </Button>
        </div>
      </form>
    </div>
  );
}
