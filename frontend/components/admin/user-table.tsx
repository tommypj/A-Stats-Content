"use client";

import { AdminUserDetail } from "@/lib/api";
import { UserRow } from "./user-row";

interface UserTableProps {
  users: AdminUserDetail[];
  onEdit: (user: AdminUserDetail) => void;
  onSuspend: (user: AdminUserDetail) => void;
  onUnsuspend: (user: AdminUserDetail) => void;
  selectedUsers: Set<string>;
  onSelectUser: (userId: string, selected: boolean) => void;
  onSelectAll: (selected: boolean) => void;
}

export function UserTable({
  users,
  onEdit,
  onSuspend,
  onUnsuspend,
  selectedUsers,
  onSelectUser,
  onSelectAll,
}: UserTableProps) {
  const allSelected = users.length > 0 && users.every((u) => selectedUsers.has(u.id));
  const someSelected = users.some((u) => selectedUsers.has(u.id)) && !allSelected;

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-surface-secondary sticky top-0 z-10">
          <tr className="border-b border-surface-tertiary">
            <th className="p-2 sm:p-3 md:p-4 text-left">
              <input
                type="checkbox"
                checked={allSelected}
                ref={(input) => {
                  if (input) input.indeterminate = someSelected;
                }}
                onChange={(e) => onSelectAll(e.target.checked)}
                className="h-4 w-4 rounded border-surface-tertiary text-primary-500 focus:ring-primary-500"
              />
            </th>
            <th className="p-2 sm:p-3 md:p-4 text-left text-sm font-semibold text-text-primary">
              User
            </th>
            <th className="p-2 sm:p-3 md:p-4 text-left text-sm font-semibold text-text-primary hidden md:table-cell">
              Role
            </th>
            <th className="p-2 sm:p-3 md:p-4 text-left text-sm font-semibold text-text-primary hidden lg:table-cell">
              Subscription
            </th>
            <th className="p-2 sm:p-3 md:p-4 text-left text-sm font-semibold text-text-primary hidden lg:table-cell">
              Created
            </th>
            <th className="p-2 sm:p-3 md:p-4 text-left text-sm font-semibold text-text-primary">
              Status
            </th>
            <th className="p-2 sm:p-3 md:p-4 text-left text-sm font-semibold text-text-primary">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <UserRow
              key={user.id}
              user={user}
              onEdit={onEdit}
              onSuspend={onSuspend}
              onUnsuspend={onUnsuspend}
              isSelected={selectedUsers.has(user.id)}
              onSelect={(selected) => onSelectUser(user.id, selected)}
            />
          ))}
        </tbody>
      </table>
      {users.length === 0 && (
        <div className="p-8 text-center text-text-muted">No users found</div>
      )}
    </div>
  );
}
