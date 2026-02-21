"use client";

import { forwardRef, HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "bg-primary-100 text-primary-700 border border-primary-200",
        secondary: "bg-surface-secondary text-text-primary border border-surface-tertiary",
        success: "bg-green-100 text-green-700 border border-green-200",
        warning: "bg-yellow-100 text-yellow-700 border border-yellow-200",
        danger: "bg-red-100 text-red-700 border border-red-200",
        outline: "border border-surface-tertiary bg-transparent text-text-primary",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(badgeVariants({ variant }), className)}
        {...props}
      />
    );
  }
);

Badge.displayName = "Badge";

export { Badge, badgeVariants };
