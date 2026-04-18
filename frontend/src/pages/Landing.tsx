/**
 * Marketing Landing Page — "The Constellation"
 *
 * Public route at `/`. Composes the nine landing section components
 * defined in `src/components/landing/`. See docs/specs/landing-page-and-design-polish.md §3.
 */
import { HeroSection } from "@/components/landing/HeroSection";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { ReceiptsSection } from "@/components/landing/ReceiptsSection";
import { OllamaSection } from "@/components/landing/OllamaSection";
import { CTARailSection } from "@/components/landing/CTARailSection";
import { DataSourcesSection } from "@/components/landing/DataSourcesSection";
import { TeamSection } from "@/components/landing/TeamSection";
import { LandingFooter } from "@/components/landing/LandingFooter";

export function Landing() {
  return (
    <main id="landing-root" className="min-h-screen bg-bp-void">
      <HeroSection />
      <ProblemSection />
      <HowItWorksSection />
      <ReceiptsSection />
      <OllamaSection />
      <CTARailSection />
      <DataSourcesSection />
      <TeamSection />
      <LandingFooter />
    </main>
  );
}
