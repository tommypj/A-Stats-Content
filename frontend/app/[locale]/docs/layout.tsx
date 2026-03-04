import PublicNav from "@/components/landing/PublicNav";
import PublicFooter from "@/components/landing/PublicFooter";
import DocsSidebar from "@/components/docs/DocsSidebar";

export const metadata = {
  title: "Documentation — A-Stats",
  description: "Learn how to use A-Stats to create AI-powered content, track SEO performance, and grow your audience.",
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <PublicNav />
      <div className="flex-1 pt-24 pb-16">
        <div className="page-container flex gap-12">
          <DocsSidebar />
          <main className="flex-1 min-w-0">{children}</main>
        </div>
      </div>
      <PublicFooter />
    </div>
  );
}
