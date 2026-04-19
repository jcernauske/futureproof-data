/**
 * Marketing Landing Page — "The Constellation"
 *
 * Public route at `/`. Composes the nine landing section components
 * defined in `src/components/landing/`. See docs/specs/landing-page-and-design-polish.md §3.
 */
import { GlobalAmbience } from "@/components/landing/GlobalAmbience";
import { LandingTopNav } from "@/components/landing/LandingTopNav";
import { HeroSection } from "@/components/landing/HeroSection";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { ReceiptsSection } from "@/components/landing/ReceiptsSection";
import { OllamaSection } from "@/components/landing/OllamaSection";
import { CTARailSection } from "@/components/landing/CTARailSection";
import { DataSourcesSection } from "@/components/landing/DataSourcesSection";
import { TeamSection } from "@/components/landing/TeamSection";
import { HorizonFooter } from "@/components/horizon/HorizonFooter";

export function Landing() {
  return (
    <main id="landing-root" className="relative min-h-screen">
      <GlobalAmbience />
      <LandingTopNav />
      <HeroSection />
      <ProblemSection />
      <HowItWorksSection />
      <ReceiptsSection />
      <OllamaSection />
      <CTARailSection />
      <DataSourcesSection />
      <TeamSection />
      <HorizonFooter />
    </main>
  );
}
