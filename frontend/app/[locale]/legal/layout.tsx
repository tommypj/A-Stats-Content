import Link from "next/link";

export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-healing-cream">
      {/* Nav */}
      <header className="border-b border-surface-tertiary bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
          <Link href="/" className="font-semibold text-text-primary text-sm tracking-tight">
            A-Stats Content
          </Link>
          <Link
            href="/"
            className="text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            ← Back to home
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 py-12">{children}</main>

      {/* Footer */}
      <footer className="border-t border-surface-tertiary mt-16">
        <div className="max-w-4xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-text-muted">
            &copy; {new Date().getFullYear()} A-Stats. All rights reserved.
          </p>
          <div className="flex items-center gap-6 text-xs text-text-muted">
            <Link href="/legal/privacy" className="hover:text-text-primary transition-colors">Privacy Policy</Link>
            <Link href="/legal/terms" className="hover:text-text-primary transition-colors">Terms of Service</Link>
            <Link href="/legal/cookies" className="hover:text-text-primary transition-colors">Cookie Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
