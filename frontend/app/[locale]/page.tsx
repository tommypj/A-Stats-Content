"use client";

import Link from "next/link";
import {
  Sparkles,
  FileText,
  Image as ImageIcon,
  BarChart3,
  ArrowRight,
  Check,
} from "lucide-react";

const features = [
  {
    icon: FileText,
    title: "AI-Powered Outlines",
    description:
      "Generate comprehensive article outlines based on your keywords and target audience.",
  },
  {
    icon: Sparkles,
    title: "Smart Content Generation",
    description:
      "Create SEO-optimized articles with therapeutic, healing-focused language.",
  },
  {
    icon: ImageIcon,
    title: "AI Image Creation",
    description:
      "Generate custom images that match your content and brand aesthetic.",
  },
  {
    icon: BarChart3,
    title: "SEO Analytics",
    description:
      "Track performance with Google Search Console integration and insights.",
  },
];

const plans = [
  {
    name: "Starter",
    price: "$29",
    period: "/month",
    description: "Perfect for small wellness blogs",
    features: [
      "10 articles per month",
      "Basic SEO optimization",
      "5 AI images",
      "Email support",
    ],
  },
  {
    name: "Professional",
    price: "$79",
    period: "/month",
    description: "For growing therapeutic practices",
    features: [
      "50 articles per month",
      "Advanced SEO tools",
      "25 AI images",
      "WordPress integration",
      "Priority support",
    ],
    popular: true,
  },
  {
    name: "Enterprise",
    price: "$199",
    period: "/month",
    description: "For wellness content agencies",
    features: [
      "Unlimited articles",
      "Full SEO suite",
      "Unlimited AI images",
      "Custom integrations",
      "Dedicated support",
      "API access",
    ],
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-surface-tertiary">
        <div className="page-container">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-primary-400 to-primary-600" />
              <span className="font-display text-xl font-semibold text-text-primary">
                A-Stats Content
              </span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <Link
                href="#features"
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Features
              </Link>
              <Link
                href="#pricing"
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Pricing
              </Link>
              <Link
                href="/login"
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Sign In
              </Link>
              <Link href="/register" className="btn-primary">
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4">
        <div className="page-container text-center">
          <div className="inline-flex items-center gap-2 rounded-full bg-primary-50 px-4 py-1.5 text-sm text-primary-600 mb-6">
            <Sparkles className="h-4 w-4" />
            <span>AI-Powered Content Creation</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-display font-bold text-text-primary max-w-4xl mx-auto leading-tight">
            Create Healing Content That{" "}
            <span className="gradient-text">Ranks & Converts</span>
          </h1>
          <p className="mt-6 text-lg text-text-secondary max-w-2xl mx-auto">
            Generate SEO-optimized therapeutic content with AI. From outlines to
            full articles and custom images, build your wellness brand
            effortlessly.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/register" className="btn-primary text-base px-8 py-3">
              Start Free Trial
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
            <Link href="#features" className="btn-secondary text-base px-8 py-3">
              See How It Works
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="page-container">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              Everything You Need for Content Success
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              Our AI understands therapeutic language and SEO best practices to
              help you create content that resonates and ranks.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="card p-6 hover:shadow-md transition-shadow"
              >
                <div className="h-12 w-12 rounded-xl bg-primary-50 flex items-center justify-center mb-4">
                  <feature.icon className="h-6 w-6 text-primary-500" />
                </div>
                <h3 className="font-display text-lg font-semibold text-text-primary mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-text-secondary">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-healing-cream">
        <div className="page-container">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-display font-bold text-text-primary">
              Simple, Transparent Pricing
            </h2>
            <p className="mt-4 text-text-secondary max-w-2xl mx-auto">
              Choose the plan that fits your content needs. Upgrade or downgrade
              anytime.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`card p-8 relative ${
                  plan.popular
                    ? "border-primary-500 shadow-lg scale-105"
                    : "border-surface-tertiary"
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-primary-500 text-white text-xs font-medium px-3 py-1 rounded-full">
                    Most Popular
                  </div>
                )}
                <div className="text-center mb-6">
                  <h3 className="font-display text-xl font-semibold text-text-primary">
                    {plan.name}
                  </h3>
                  <p className="text-sm text-text-secondary mt-1">
                    {plan.description}
                  </p>
                  <div className="mt-4">
                    <span className="text-4xl font-display font-bold text-text-primary">
                      {plan.price}
                    </span>
                    <span className="text-text-muted">{plan.period}</span>
                  </div>
                </div>
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-3 text-sm">
                      <Check className="h-4 w-4 text-healing-sage flex-shrink-0" />
                      <span className="text-text-secondary">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className={`w-full ${
                    plan.popular ? "btn-primary" : "btn-secondary"
                  }`}
                >
                  Get Started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-br from-primary-500 to-primary-600">
        <div className="page-container text-center">
          <h2 className="text-3xl md:text-4xl font-display font-bold text-white">
            Ready to Transform Your Content?
          </h2>
          <p className="mt-4 text-primary-100 max-w-2xl mx-auto">
            Join hundreds of wellness professionals creating better content with
            AI.
          </p>
          <Link
            href="/register"
            className="mt-8 inline-flex btn bg-white text-primary-600 hover:bg-primary-50 px-8 py-3"
          >
            Start Your Free Trial
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-text-primary">
        <div className="page-container">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-md bg-gradient-to-br from-primary-400 to-primary-600" />
              <span className="font-display text-lg font-semibold text-white">
                A-Stats Content
              </span>
            </div>
            <p className="text-sm text-text-muted">
              &copy; {new Date().getFullYear()} A-Stats. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
