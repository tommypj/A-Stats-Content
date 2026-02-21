import React from "react";
import { User, Users } from "lucide-react";
import { clsx } from "clsx";
import Image from "next/image";

interface ContentOwnershipBadgeProps {
  teamId?: string;
  teamName?: string;
  teamLogoUrl?: string;
  isPersonal: boolean;
  variant?: "default" | "compact" | "detailed";
  className?: string;
}

export function ContentOwnershipBadge({
  teamId,
  teamName,
  teamLogoUrl,
  isPersonal,
  variant = "default",
  className,
}: ContentOwnershipBadgeProps) {
  if (variant === "compact") {
    return (
      <span
        className={clsx(
          "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium",
          isPersonal
            ? "bg-blue-50 text-blue-700 border border-blue-200"
            : "bg-purple-50 text-purple-700 border border-purple-200",
          className
        )}
      >
        {isPersonal ? (
          <User className="h-3 w-3" />
        ) : teamLogoUrl ? (
          <Image
            src={teamLogoUrl}
            alt={teamName || "Team"}
            width={12}
            height={12}
            className="h-3 w-3 rounded-full object-cover"
          />
        ) : (
          <Users className="h-3 w-3" />
        )}
        {isPersonal ? "Personal" : teamName || "Team"}
      </span>
    );
  }

  if (variant === "detailed") {
    return (
      <div
        className={clsx(
          "flex items-center gap-3 p-3 rounded-lg border",
          isPersonal
            ? "bg-blue-50/50 border-blue-200"
            : "bg-purple-50/50 border-purple-200",
          className
        )}
      >
        <div
          className={clsx(
            "flex items-center justify-center h-10 w-10 rounded-full",
            isPersonal ? "bg-blue-100" : "bg-purple-100"
          )}
        >
          {isPersonal ? (
            <User className="h-5 w-5 text-blue-600" />
          ) : teamLogoUrl ? (
            <Image
              src={teamLogoUrl}
              alt={teamName || "Team"}
              width={40}
              height={40}
              className="h-10 w-10 rounded-full object-cover"
            />
          ) : (
            <Users className="h-5 w-5 text-purple-600" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-text-secondary">Owned by</p>
          <p
            className={clsx(
              "text-sm font-medium truncate",
              isPersonal ? "text-blue-700" : "text-purple-700"
            )}
          >
            {isPersonal ? "Personal Workspace" : teamName || "Team Workspace"}
          </p>
        </div>
      </div>
    );
  }

  // Default variant
  return (
    <div
      className={clsx(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-lg",
        isPersonal
          ? "bg-blue-50 text-blue-700 border border-blue-200"
          : "bg-purple-50 text-purple-700 border border-purple-200",
        className
      )}
    >
      {isPersonal ? (
        <User className="h-4 w-4" />
      ) : teamLogoUrl ? (
        <Image
          src={teamLogoUrl}
          alt={teamName || "Team"}
          width={16}
          height={16}
          className="h-4 w-4 rounded-full object-cover"
        />
      ) : (
        <Users className="h-4 w-4" />
      )}
      <span className="text-sm font-medium">
        {isPersonal ? "Personal" : teamName || "Team"}
      </span>
    </div>
  );
}
