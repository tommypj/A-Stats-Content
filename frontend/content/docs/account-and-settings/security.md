## Accessing Security Settings

Security settings are in **Settings > Password** (for password management) and **Settings > Security** (for session and account security). These settings protect your account from unauthorized access.

## Changing Your Password

To change your password:

1. Navigate to **Settings > Password**.
2. Enter your **current password** in the first field.
3. Enter a **new password** in the second field.
4. Confirm the new password in the third field.
5. Click **Update Password**.

### Password Requirements
- Minimum 8 characters
- At least one uppercase letter
- At least one number or special character

Strong passwords use a mix of letters, numbers, and symbols, or a passphrase of four or more unrelated words. Avoid using the same password you use for other services.

> **Tip:** Use a password manager (1Password, Bitwarden, Dashlane) to generate and store a strong unique password. This is the single highest-impact step you can take for account security.

### After Changing Your Password
- All existing login sessions (on other devices or browsers) are **immediately invalidated** when you change your password. Any device currently logged in is signed out and must log in again with the new password.
- You remain logged in on the current device automatically after the change.

### Forgotten Password
If you cannot log in because you have forgotten your password, use the **Forgot Password** link on the login page. You will receive a password reset email at the address on file. The reset link expires after 24 hours.

## Session Management

Sessions represent active logins to your account — each browser or device where you are currently signed in creates a session.

### Viewing Active Sessions
Navigate to **Settings > Security**. The Sessions section lists all current active sessions, showing:
- Device type and browser (for example, "Chrome on Windows")
- Approximate location based on IP address
- Last active timestamp
- Whether it is the current session (marked "This device")

### Session Limits by Plan

The platform enforces session limits to reduce the risk of credential sharing or unauthorized access:

| Plan | Active Sessions Allowed |
|------|------------------------|
| Free | 2 |
| Starter | 5 |
| Pro | 10 |
| Enterprise | 20 |

When you log in and would exceed your session limit, the oldest inactive session is automatically removed to make room for the new one.

### Revoking a Session
To sign out a specific session (for example, a device you no longer have or a session you do not recognize):

1. Find the session in the list.
2. Click **Revoke** next to that session.
3. Confirm the revocation.

The session is terminated immediately. If someone is actively using that session, they are signed out and must log in again.

### Signing Out All Sessions
Click **Sign Out All Other Sessions** to revoke every session except the current one. Use this if you believe your account credentials may have been compromised. After revoking all sessions, change your password immediately.

## Token Security and Logout

When you log out, both your access token and refresh token are invalidated on the server. This means logging out from one device cannot be replayed or reused. If your browser is closed without logging out (for example, the browser crashes), the session remains valid until it naturally expires.

For maximum security on shared or public devices, always click the **Log Out** button rather than simply closing the browser.

## Remember Me

The login form includes a **Remember Me** checkbox.

- **With Remember Me checked:** Your session extends for **30 days** of inactivity before expiring. You will not need to log in again for a month of regular use.
- **Without Remember Me checked:** Your session expires after **7 days** of inactivity.

On shared computers, always leave Remember Me unchecked to reduce the risk of someone else accessing your account on the same browser.

## Google Sign-In

If you signed up using Google OAuth ("Sign in with Google"), your password is managed by your Google account. You cannot set a platform-specific password in this case. To manage security for a Google-authenticated account:

- Change your Google account password at myaccount.google.com
- Enable Google's two-factor authentication for your Google account
- Review which apps have access to your Google account periodically

## Suspicious Activity

If you see sessions or activity you do not recognize:

1. Revoke all other sessions from **Settings > Security**.
2. Change your password immediately at **Settings > Password**.
3. Review whether your email account (used for login) may also be compromised.
4. Contact support if you need help securing your account.
