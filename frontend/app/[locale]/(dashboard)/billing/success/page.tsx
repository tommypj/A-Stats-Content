"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle, Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, parseApiError, SubscriptionStatus } from "@/lib/api";
import { toast } from "sonner";

export default function CheckoutSuccessPage() {
  const router = useRouter();
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      setLoading(true);
      const data = await api.billing.subscription();
      setSubscription(data);
    } catch (error) {
      const apiError = parseApiError(error);
      toast.error(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface to-surface-secondary">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface to-surface-secondary p-4">
      <Card className="max-w-2xl w-full">
        <CardContent className="p-8 md:p-12">
          <div className="text-center">
            {/* Success Icon */}
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-100 mb-6">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>

            {/* Success Message */}
            <h1 className="font-display text-3xl md:text-4xl font-bold text-text-primary mb-4">
              Welcome to {subscription?.subscription_tier || "Premium"}!
            </h1>
            <p className="text-lg text-text-secondary mb-8">
              Your subscription has been activated successfully. You now have access to all premium
              features.
            </p>

            {/* Plan Details */}
            {subscription && (
              <div className="bg-gradient-to-r from-primary-50 to-purple-50 rounded-xl p-6 mb-8">
                <div className="flex items-center justify-center gap-2 mb-4">
                  <Sparkles className="h-5 w-5 text-primary-500" />
                  <h2 className="font-display text-xl font-semibold text-text-primary">
                    Your New Plan
                  </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                  <div className="bg-surface rounded-lg p-4">
                    <p className="text-sm text-text-muted mb-1">Subscription Tier</p>
                    <p className="font-semibold text-text-primary capitalize">
                      {subscription.subscription_tier}
                    </p>
                  </div>
                  <div className="bg-surface rounded-lg p-4">
                    <p className="text-sm text-text-muted mb-1">Status</p>
                    <div className="flex items-center gap-2">
                      <Badge variant="success">Active</Badge>
                    </div>
                  </div>
                  {subscription.subscription_expires && (
                    <div className="bg-surface rounded-lg p-4 md:col-span-2">
                      <p className="text-sm text-text-muted mb-1">Next Renewal Date</p>
                      <p className="font-semibold text-text-primary">
                        {new Date(subscription.subscription_expires).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        })}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* What's Next */}
            <div className="text-left mb-8">
              <h3 className="font-display text-lg font-semibold text-text-primary mb-4">
                What's next?
              </h3>
              <ul className="space-y-3">
                <li className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-primary-600 font-semibold text-sm">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">Create your first article</p>
                    <p className="text-sm text-text-secondary">
                      Head to the Articles page and start generating high-quality content
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-primary-600 font-semibold text-sm">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">Connect your WordPress site</p>
                    <p className="text-sm text-text-secondary">
                      Publish content directly to your website with one click
                    </p>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-primary-600 font-semibold text-sm">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">Track your analytics</p>
                    <p className="text-sm text-text-secondary">
                      Connect Google Search Console to monitor your content performance
                    </p>
                  </div>
                </li>
              </ul>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button
                variant="primary"
                size="lg"
                onClick={() => router.push("/articles")}
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                Go to Dashboard
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => router.push("/settings/billing")}
              >
                View Billing Settings
              </Button>
            </div>

            {/* Support */}
            <div className="mt-8 pt-8 border-t border-surface-tertiary">
              <p className="text-sm text-text-muted">
                Need help getting started?{" "}
                <a href="mailto:support@astats.com" className="text-primary-500 hover:underline">
                  Contact our support team
                </a>
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
