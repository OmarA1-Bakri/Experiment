"use client";


import { motion } from "framer-motion";
import {
  Shield,
  FileCheck,
  Users,
  WandSparkles,
  Gauge,
  Mail,
  MapPin,
  MousePointerClick,
  TrendingUpIcon,
  CheckCircle2,
  Star,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/lib/stores/auth.store";
import { cn } from "@/lib/utils";

import type React from "react"


// Benefit Card Component
interface BenefitCardProps {
  title: string;
  description: string;
  stats: string;
}

const BenefitCard = ({ title, description, stats }: BenefitCardProps) => {
  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      transition={{ type: "spring", stiffness: 300 }}
      className="bg-gradient-to-br from-card to-card/50 p-8 rounded-2xl border border-border hover:border-gold/50 transition-all duration-300"
    >
      <h3 className="text-2xl font-semibold text-foreground mb-4">{title}</h3>
      <p className="text-muted-foreground text-sm leading-relaxed mb-4">{description}</p>
      <div className="text-gold font-medium text-sm">{stats}</div>
    </motion.div>
  );
};

// Testimonial Card Component
interface TestimonialCardProps {
  quote: string;
  author: string;
  title: string;
  company: string;
  rating: number;
}

const TestimonialCard = ({ quote, author, title, company, rating }: TestimonialCardProps) => {
  return (
    <div className="bg-gradient-to-br from-card to-card/50 p-6 rounded-2xl border border-border hover:border-gold/50 transition-all duration-300">
      <div className="flex mb-4">
        {[...Array(rating)].map((_, i) => (
          <Star key={i} className="w-4 h-4 fill-gold text-gold" />
        ))}
      </div>
      <p className="text-muted-foreground text-sm leading-relaxed mb-6 italic">&quot;{quote}&quot;</p>
      <div className="border-t border-border pt-4">
        <p className="text-foreground font-semibold">{author}</p>
        <p className="text-gold text-sm">{title}</p>
        <p className="text-muted-foreground text-xs">{company}</p>
      </div>
    </div>
  );
};

// Feature Card Component
interface FeatureCardProps {
  title: string;
  text: string;
  icon: React.ReactNode;
}

const FeatureCard = ({ title, text, icon }: FeatureCardProps) => {
  return (
    <div className="flex flex-col items-center text-center p-8 hover:bg-muted/30 rounded-lg transition-colors">
      <div className="text-gold mb-4">{icon}</div>
      <h3 className="text-xl font-semibold text-foreground mb-4">{title}</h3>
      <p className="text-muted-foreground text-sm leading-relaxed">{text}</p>
    </div>
  );
};

// Pricing Card Component
interface PricingCardProps {
  title: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  buttonText: string;
  popular: boolean;
  onSelect: () => void;
}

const PricingCard = ({
  title,
  price,
  period,
  description,
  features,
  buttonText,
  popular,
  onSelect,
}: PricingCardProps) => {
  return (
    <div
      className={cn(
        "relative bg-gradient-to-br from-card to-card/50 p-8 rounded-2xl border transition-all duration-300 hover:transform hover:scale-105",
        popular
          ? "border-gold shadow-lg shadow-gold/20"
          : "border-border hover:border-gold/50"
      )}
    >
      {popular && (
        <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
          <span className="bg-gradient-to-r from-gold to-gold-dark text-white px-4 py-1 rounded-full text-sm font-medium">
            Most Popular
          </span>
        </div>
      )}

      <div className="text-center mb-6">
        <h3 className="text-2xl font-bold text-foreground mb-2">{title}</h3>
        <div className="mb-2">
          <span className="text-4xl font-bold text-foreground">{price}</span>
          {price !== "Custom" && <span className="text-muted-foreground text-lg">/{period}</span>}
        </div>
        <p className="text-muted-foreground text-sm">{description}</p>
      </div>

      <ul className="space-y-3 mb-8">
        {features.map((feature, index) => (
          <li key={index} className="flex items-center text-muted-foreground text-sm">
            <CheckCircle2 className="w-4 h-4 text-gold mr-3 flex-shrink-0" />
            {feature}
          </li>
        ))}
      </ul>

      <Button
        className={cn(
          "w-full",
          popular
            ? "bg-gold hover:bg-gold-dark text-navy"
            : "bg-transparent border border-gold text-gold hover:bg-gold hover:text-navy"
        )}
        onClick={onSelect}
      >
        {buttonText}
      </Button>
    </div>
  );
};

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Remove automatic redirect to prevent flash of content
  // Users can navigate manually using the navigation

  // Don't render animations until mounted to avoid hydration issues
  if (!mounted) {
    return (
      <div className="relative min-h-screen w-full overflow-hidden bg-background">
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <h1 className="text-7xl md:text-8xl font-bold tracking-tight">
              <span className="text-navy">rule</span>
              <span className="text-gold">IQ</span>
            </h1>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-background">
      {/* Navigation Header */}
      <header className="absolute top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-sm border-b">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold">
              <span className="text-navy">rule</span>
              <span className="text-gold">IQ</span>
            </h1>
          </Link>
          <div className="flex items-center gap-4">
            {mounted && isAuthenticated ? (
              <>
                <Button
                  variant="ghost"
                  className="text-navy hover:text-gold"
                  onClick={() => router.push("/dashboard")}
                >
                  Go to Dashboard
                </Button>
                <Button
                  variant="outline"
                  className="border-navy text-navy hover:bg-navy hover:text-white"
                  onClick={() => {
                    useAuthStore.getState().logout();
                    router.push("/");
                  }}
                >
                  Sign Out
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="ghost"
                  className="text-navy hover:text-gold"
                  onClick={() => router.push("/login")}
                >
                  Sign In
                </Button>
                <Button
                  className="bg-gold hover:bg-gold-dark text-navy"
                  onClick={() => router.push("/signup")}
                >
                  Get Started
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative">
        <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:50px_50px]" />
        <div className="absolute h-full w-full bg-gradient-to-br from-navy/20 via-background to-background" />
        
        <div className="relative pt-32 pb-16 container mx-auto px-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center flex flex-col items-center justify-center max-w-5xl mx-auto"
          >
            {/* Transform Label */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.8 }}
              className="inline-block mb-8"
            >
              <span className="px-4 py-2 rounded-xl flex flex-row gap-3 items-center bg-gold/10 text-xs text-gold backdrop-blur-sm border border-gold/20 shadow-lg">
                <WandSparkles className="w-5 h-5 text-gold" />
                <p className="font-medium uppercase tracking-wider">
                  Transform Your Compliance with AI Automation
                </p>
              </span>
            </motion.div>

            {/* Main Title */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.4, duration: 1, ease: "easeOut" }}
              className="mb-8"
            >
              <h1 className="text-7xl md:text-8xl font-bold tracking-tight">
                <span className="text-navy">rule</span>
                <span className="text-gold">IQ</span>
              </h1>
            </motion.div>

            {/* Tagline */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.8 }}
              className="mb-8"
            >
              <h2 className="text-3xl md:text-4xl font-light text-navy/80 uppercase tracking-[0.2em]">
                AI Compliance Automated
              </h2>
            </motion.div>

            {/* Description */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8, duration: 0.8 }}
              className="max-w-3xl mx-auto text-lg text-muted-foreground text-center leading-relaxed mb-12"
            >
              Stop struggling with compliance management. Our AI-powered platform analyzes
              your business, creates personalized compliance strategies, and helps you
              execute them - all in real-time.
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1 }}
              className="flex flex-col sm:flex-row gap-4 items-center"
            >
              <Button
                size="lg"
                className="bg-gold hover:bg-gold-dark text-navy font-semibold px-8"
                onClick={() => router.push("/signup")}
              >
                Start Free Trial
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-navy text-navy hover:bg-navy hover:text-white"
                onClick={() => router.push("/login")}
              >
                Sign In
              </Button>
            </motion.div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.2 }}
              className="mt-4 text-sm text-muted-foreground"
            >
              Try ruleIQ free for 30 days. No credit card required.
            </motion.p>
          </motion.div>
        </div>
      </main>

      {/* Benefits Section */}
      <section className="py-24 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <Button variant="outline" className="rounded-full mb-8">
              Benefits
            </Button>
            <h2 className="text-4xl md:text-5xl font-light mb-4">
              Why Choose <span className="text-gold font-semibold">ruleIQ</span> for your business
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-6xl mx-auto">
            <BenefitCard
              title="Reduce Compliance Costs by 60%"
              description="Automate manual compliance tasks and reduce the need for external consultants with our AI-powered platform."
              stats="Average 60% cost reduction"
            />
            <BenefitCard
              title="Cut Audit Preparation Time by 75%"
              description="Maintain audit-ready documentation automatically with real-time evidence collection and gap analysis."
              stats="From weeks to days"
            />
            <BenefitCard
              title="Achieve 99.9% Compliance Accuracy"
              description="AI-driven monitoring ensures you never miss regulatory changes or compliance requirements."
              stats="99.9% accuracy rate"
            />
            <BenefitCard
              title="Scale Across Multiple Frameworks"
              description="Support for SOC 2, ISO 27001, HIPAA, GDPR, and 50+ other compliance frameworks in one platform."
              stats="50+ frameworks supported"
            />
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-24">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <Button variant="outline" className="rounded-full mb-8">
              Testimonials
            </Button>
            <h2 className="text-4xl md:text-5xl font-light mb-4">
              Trusted by <span className="text-gold font-semibold">Industry Leaders</span> worldwide
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
            <TestimonialCard
              quote="ruleIQ reduced our SOC 2 audit preparation time from 6 weeks to just 3 days. The automated evidence collection is a game-changer."
              author="Sarah Chen"
              title="CISO"
              company="TechFlow Solutions"
              rating={5}
            />
            <TestimonialCard
              quote="We achieved HIPAA compliance 75% faster with ruleIQ. The AI-powered gap analysis identified issues we didn't even know existed."
              author="Dr. Michael Rodriguez"
              title="Chief Compliance Officer"
              company="HealthCare Innovations"
              rating={5}
            />
            <TestimonialCard
              quote="The real-time monitoring and automated reporting saved us over $200K in compliance costs last year. ROI was immediate."
              author="Jennifer Walsh"
              title="VP of Risk Management"
              company="Global Financial Services"
              rating={5}
            />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <Button variant="outline" className="rounded-full mb-8">
              Features
            </Button>
            <h2 className="text-4xl md:text-5xl font-light mb-4">
              Feature packed to make
              <br />
              <span className="text-gold font-semibold">Compliance management easier and automated</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <FeatureCard
              title="Smart Gap Analysis"
              text="AI-powered compliance gap identification ensures your organization meets all regulatory requirements with automated evidence collection."
              icon={<MousePointerClick className="w-16 h-16" />}
            />
            <FeatureCard
              title="Real-time Monitoring"
              text="Access real-time insights and track compliance metrics across all frameworks in one unified dashboard."
              icon={<Gauge className="w-16 h-16" />}
            />
            <FeatureCard
              title="Policy Automation"
              text="Automate policy creation and maintenance with AI-driven suggestions to improve your compliance posture."
              icon={<TrendingUpIcon className="w-16 h-16" />}
            />
            <FeatureCard
              title="Risk Assessment"
              text="AI agents continuously assess compliance risks, monitor regulatory changes, and provide actionable insights."
              icon={<Shield className="w-16 h-16" />}
            />
            <FeatureCard
              title="Evidence Collection"
              text="Automated evidence gathering and documentation management help you maintain comprehensive audit trails."
              icon={<FileCheck className="w-16 h-16" />}
            />
            <FeatureCard
              title="Team Collaboration"
              text="Centralize and streamline your compliance workflows. Enable seamless collaboration across teams."
              icon={<Users className="w-16 h-16" />}
            />
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-24">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <Button variant="outline" className="rounded-full mb-8">
              Pricing
            </Button>
            <h2 className="text-4xl md:text-5xl font-light mb-4">
              Simple, transparent
              <br />
              <span className="text-gold font-semibold">pricing for every business</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <PricingCard
              title="Starter"
              price="£149"
              period="month"
              description="Perfect for small businesses getting started with compliance"
              features={[
                "Up to 2 compliance frameworks",
                "Basic AI-powered gap analysis",
                "Monthly compliance reports",
                "Email support",
                "1 user account",
              ]}
              buttonText="Start Free Trial"
              popular={false}
              onSelect={() => router.push("/signup?plan=starter")}
            />
            <PricingCard
              title="Professional"
              price="£499"
              period="month"
              description="Ideal for growing companies with complex compliance needs"
              features={[
                "Unlimited compliance frameworks",
                "Advanced AI insights & automation",
                "Real-time monitoring & alerts",
                "Priority support",
                "5 user accounts",
                "Custom policy templates",
                "API access",
              ]}
              buttonText="Start Free Trial"
              popular={true}
              onSelect={() => router.push("/signup?plan=professional")}
            />
            <PricingCard
              title="Enterprise"
              price="Custom"
              period=""
              description="Tailored solutions for large organizations"
              features={[
                "Everything in Professional",
                "Unlimited user accounts",
                "Dedicated account manager",
                "Custom integrations",
                "SLA guarantees",
                "On-premise deployment option",
                "White-label options",
              ]}
              buttonText="Contact Sales"
              popular={false}
              onSelect={() => router.push("/contact-sales")}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 bg-gradient-to-br from-navy/20 to-background">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl md:text-5xl font-light mb-8">
            Are you ready to transform
            <br />
            <span className="text-gold font-semibold">your Compliance Management?</span>
          </h2>

          <div className="flex flex-col sm:flex-row gap-4 items-center justify-center mt-12">
            <Button
              size="lg"
              className="bg-gold hover:bg-gold-dark text-navy font-semibold px-8"
              onClick={() => router.push("/signup")}
            >
              Start Free Trial
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="border-navy text-navy hover:bg-navy hover:text-white"
              onClick={() => router.push("/login")}
            >
              Get Started
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-card border-t">
        <div className="container mx-auto px-4 py-16">
          <div className="grid md:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="space-y-4">
              <h2 className="text-3xl font-bold">
                <span className="text-navy">rule</span>
                <span className="text-gold">IQ</span>
              </h2>
              <div className="space-y-2 text-sm text-muted-foreground">
                <a
                  href="mailto:contact@ruleiq.io"
                  className="flex items-center gap-2 hover:text-gold transition-colors"
                >
                  <Mail className="w-4 h-4" />
                  contact@ruleiq.io
                </a>
                <p className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  Global Compliance Solutions
                </p>
              </div>
            </div>

            {/* Company */}
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <nav className="space-y-2 text-sm text-muted-foreground">
                <Link href="/about" className="block hover:text-gold transition-colors">
                  About Us
                </Link>
                <Link href="/privacy" className="block hover:text-gold transition-colors">
                  Privacy Policy
                </Link>
                <Link href="/terms" className="block hover:text-gold transition-colors">
                  Terms of Service
                </Link>
                <Link href="/support" className="block hover:text-gold transition-colors">
                  Support
                </Link>
              </nav>
            </div>

            {/* Resources */}
            <div>
              <h3 className="font-semibold mb-4">Resources</h3>
              <nav className="space-y-2 text-sm text-muted-foreground">
                <Link href="/documentation" className="block hover:text-gold transition-colors">
                  Documentation
                </Link>
                <Link href="/blog" className="block hover:text-gold transition-colors">
                  Blog
                </Link>
                <Link href="/help" className="block hover:text-gold transition-colors">
                  Help Center
                </Link>
                <Link href="/api" className="block hover:text-gold transition-colors">
                  API Reference
                </Link>
              </nav>
            </div>

            {/* Product */}
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <nav className="space-y-2 text-sm text-muted-foreground">
                <Link href="/features" className="block hover:text-gold transition-colors">
                  Features
                </Link>
                <Link href="/pricing" className="block hover:text-gold transition-colors">
                  Pricing
                </Link>
                <Link href="/roadmap" className="block hover:text-gold transition-colors">
                  Roadmap
                </Link>
                <Link href="/changelog" className="block hover:text-gold transition-colors">
                  Changelog
                </Link>
              </nav>
            </div>
          </div>

          <div className="border-t mt-12 pt-8 text-center text-sm text-muted-foreground">
            <p>© 2025 ruleIQ. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}