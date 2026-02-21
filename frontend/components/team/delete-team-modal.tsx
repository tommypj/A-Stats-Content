"use client";

import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertTriangle } from "lucide-react";

interface DeleteTeamModalProps {
  isOpen: boolean;
  onClose: () => void;
  teamName: string;
  onDelete: () => Promise<void>;
}

export function DeleteTeamModal({
  isOpen,
  onClose,
  teamName,
  onDelete,
}: DeleteTeamModalProps) {
  const [confirmText, setConfirmText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const isConfirmed = confirmText === teamName;

  const handleDelete = async () => {
    if (!isConfirmed) {
      alert("Please type the team name to confirm deletion");
      return;
    }

    setIsLoading(true);
    try {
      await onDelete();
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      setConfirmText("");
      onClose();
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={handleClose} title="Delete Team">
      <div className="space-y-4">
        {/* Warning */}
        <div className="p-4 rounded-lg bg-red-50 border border-red-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium text-red-900 mb-1">Permanent Deletion</p>
              <p className="text-sm text-red-800">
                This action cannot be undone. All team data, including articles, outlines, images, and settings will be permanently deleted. Team members will lose access immediately.
              </p>
            </div>
          </div>
        </div>

        {/* Confirmation Input */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Type <span className="font-bold text-text-primary">{teamName}</span> to confirm
          </label>
          <Input
            value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)}
            placeholder="Enter team name"
            disabled={isLoading}
            autoComplete="off"
          />
          <p className="text-xs text-text-muted mt-1">
            This is case-sensitive and must match exactly
          </p>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4">
          <Button variant="outline" onClick={handleClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleDelete}
            isLoading={isLoading}
            disabled={!isConfirmed}
          >
            Delete Team Forever
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
