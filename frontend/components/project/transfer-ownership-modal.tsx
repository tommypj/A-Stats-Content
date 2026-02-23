"use client";

import { useState } from "react";
import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ProjectMember } from "@/lib/api";
import { Crown, AlertTriangle } from "lucide-react";

interface TransferOwnershipModalProps {
  isOpen: boolean;
  onClose: () => void;
  members: ProjectMember[];
  onTransfer: (newOwnerId: string) => Promise<void>;
}

export function TransferOwnershipModal({
  isOpen,
  onClose,
  members,
  onTransfer,
}: TransferOwnershipModalProps) {
  const [selectedMember, setSelectedMember] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);

  // Filter out owner and viewers
  const eligibleMembers = members.filter(
    (m) => m.role === "admin" || m.role === "member"
  );

  const handleTransfer = async () => {
    if (!selectedMember) {
      alert("Please select a member to transfer ownership to");
      return;
    }

    const member = members.find((m) => m.user_id === selectedMember);
    if (!member) return;

    if (!confirm(`Are you sure you want to transfer ownership to ${member.name}? This action cannot be undone and you will become an Admin.`)) {
      return;
    }

    setIsLoading(true);
    try {
      await onTransfer(selectedMember);
      onClose();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Transfer Project Ownership">
      <div className="space-y-4">
        {/* Warning */}
        <div className="p-4 rounded-lg bg-yellow-50 border border-yellow-200">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium text-yellow-900 mb-1">Important Warning</p>
              <p className="text-sm text-yellow-800">
                Transferring ownership is permanent. You will lose owner privileges and become an Admin. The new owner will have full control over the project, including the ability to remove you.
              </p>
            </div>
          </div>
        </div>

        {/* Member Selection */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-3">
            Select New Owner
          </label>

          {eligibleMembers.length === 0 ? (
            <p className="text-sm text-text-muted">
              No eligible members found. Only Admins and Members can become project owners.
            </p>
          ) : (
            <div className="space-y-2">
              {eligibleMembers.map((member) => (
                <label
                  key={member.id}
                  className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedMember === member.user_id
                      ? "border-primary-500 bg-primary-50"
                      : "border-surface-tertiary hover:border-primary-200"
                  }`}
                >
                  <input
                    type="radio"
                    name="newOwner"
                    value={member.user_id}
                    checked={selectedMember === member.user_id}
                    onChange={(e) => setSelectedMember(e.target.value)}
                    className="sr-only"
                    disabled={isLoading}
                  />
                  <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
                    {member.avatar_url ? (
                      <img
                        src={member.avatar_url}
                        alt={member.name}
                        className="h-full w-full rounded-full object-cover"
                      />
                    ) : (
                      <span className="text-sm font-medium text-primary-600">
                        {member.name.charAt(0).toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-text-primary">{member.name}</p>
                    <p className="text-sm text-text-muted">{member.email}</p>
                  </div>
                  <Crown
                    className={`h-5 w-5 ${
                      selectedMember === member.user_id ? "text-yellow-500" : "text-gray-300"
                    }`}
                  />
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-4">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleTransfer}
            isLoading={isLoading}
            disabled={!selectedMember || eligibleMembers.length === 0}
          >
            Transfer Ownership
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
