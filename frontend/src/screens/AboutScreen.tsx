import { motion } from "framer-motion";
import { PageContainer } from "@/components/ui/PageContainer";
import { springs, stagger, staggerContainer, staggerItem } from "@/styles/motion";
import { useT } from "@/i18n/useT";
import { SourceCard, type SourceCardVariant } from "@/components/about/SourceCard";

/**
 * AboutScreen — the "show your work" page.
 *
 * Trust through transparency: a counselor lands here skeptical and leaves
 * convinced. Eleven public datasets, one model layer, every URL clickable.
 *
 * Sections: header, why-this-exists, pipeline (Bronze/Silver/Gold strip),
 * receipts grid (12 SourceCards), closing trust line.
 */

interface SourceEntry {
  id: string;
  variant: SourceCardVariant;
  titleKey: string;
  publisherKey: string;
  vintage: string;
  blurbKey: string;
  caveatKey?: string;
  displayUrl: string;
  href: string;
}

const SOURCES: SourceEntry[] = [
  {
    id: "scorecard-field",
    variant: "gov",
    titleKey: "about.sources.scorecardField.title",
    publisherKey: "about.sources.scorecardField.publisher",
    vintage: "2023–24 cohort",
    blurbKey: "about.sources.scorecardField.blurb",
    caveatKey: "about.sources.scorecardField.caveat",
    displayUrl: "collegescorecard.ed.gov/data",
    href: "https://collegescorecard.ed.gov/data/",
  },
  {
    id: "scorecard-institution",
    variant: "gov",
    titleKey: "about.sources.scorecardInstitution.title",
    publisherKey: "about.sources.scorecardInstitution.publisher",
    vintage: "2023–24 cohort",
    blurbKey: "about.sources.scorecardInstitution.blurb",
    displayUrl: "collegescorecard.ed.gov/data",
    href: "https://collegescorecard.ed.gov/data/",
  },
  {
    id: "bls-ooh",
    variant: "gov",
    titleKey: "about.sources.blsOoh.title",
    publisherKey: "about.sources.blsOoh.publisher",
    vintage: "2024–34 projections",
    blurbKey: "about.sources.blsOoh.blurb",
    displayUrl: "bls.gov/emp",
    href: "https://www.bls.gov/emp/",
  },
  {
    id: "onet",
    variant: "gov",
    titleKey: "about.sources.onet.title",
    publisherKey: "about.sources.onet.publisher",
    vintage: "v30.2 (Oct 2024)",
    blurbKey: "about.sources.onet.blurb",
    displayUrl: "onetcenter.org",
    href: "https://www.onetcenter.org/database.html",
  },
  {
    id: "cip-soc",
    variant: "gov",
    titleKey: "about.sources.cipSoc.title",
    publisherKey: "about.sources.cipSoc.publisher",
    vintage: "CIP 2020 × SOC 2018",
    blurbKey: "about.sources.cipSoc.blurb",
    caveatKey: "about.sources.cipSoc.caveat",
    displayUrl: "nces.ed.gov/ipeds/cipcode",
    href: "https://nces.ed.gov/ipeds/cipcode/",
  },
  {
    id: "karpathy",
    variant: "acad",
    titleKey: "about.sources.karpathy.title",
    publisherKey: "about.sources.karpathy.publisher",
    vintage: "Late 2024 snapshot",
    blurbKey: "about.sources.karpathy.blurb",
    caveatKey: "about.sources.karpathy.caveat",
    displayUrl: "github.com/karpathy/jobs",
    href: "https://github.com/karpathy/jobs",
  },
  {
    id: "anthropic-econ",
    variant: "priv",
    titleKey: "about.sources.anthropicEcon.title",
    publisherKey: "about.sources.anthropicEcon.publisher",
    vintage: "Release 2025-03-27",
    blurbKey: "about.sources.anthropicEcon.blurb",
    caveatKey: "about.sources.anthropicEcon.caveat",
    displayUrl: "anthropic.com/economic-index",
    href: "https://www.anthropic.com/economic-index",
  },
  {
    id: "bea-rpp",
    variant: "gov",
    titleKey: "about.sources.beaRpp.title",
    publisherKey: "about.sources.beaRpp.publisher",
    vintage: "2024 release",
    blurbKey: "about.sources.beaRpp.blurb",
    displayUrl: "bea.gov/data",
    href: "https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area",
  },
  {
    id: "ipeds-finance",
    variant: "gov",
    titleKey: "about.sources.ipedsFinance.title",
    publisherKey: "about.sources.ipedsFinance.publisher",
    vintage: "FY2024",
    blurbKey: "about.sources.ipedsFinance.blurb",
    displayUrl: "nces.ed.gov/ipeds",
    href: "https://nces.ed.gov/ipeds/",
  },
  {
    id: "eada",
    variant: "gov",
    titleKey: "about.sources.eada.title",
    publisherKey: "about.sources.eada.publisher",
    vintage: "FY2024",
    blurbKey: "about.sources.eada.blurb",
    caveatKey: "about.sources.eada.caveat",
    displayUrl: "ope.ed.gov/athletics",
    href: "https://ope.ed.gov/athletics/",
  },
  {
    id: "bls-oews",
    variant: "gov",
    titleKey: "about.sources.blsOews.title",
    publisherKey: "about.sources.blsOews.publisher",
    vintage: "May 2024",
    blurbKey: "about.sources.blsOews.blurb",
    displayUrl: "bls.gov/oes",
    href: "https://www.bls.gov/oes/",
  },
  {
    id: "gemma-4",
    variant: "model",
    titleKey: "about.sources.gemma.title",
    publisherKey: "about.sources.gemma.publisher",
    vintage: "v4",
    blurbKey: "about.sources.gemma.blurb",
    displayUrl: "ai.google.dev/gemma",
    href: "https://ai.google.dev/gemma",
  },
];

function PipelineStep({
  zoneKey,
  accentClass,
  titleKey,
  bodyKey,
}: {
  zoneKey: string;
  accentClass: string;
  titleKey: string;
  bodyKey: string;
}) {
  const t = useT();
  return (
    <div className="rounded-xl bg-bp-mid border border-border-subtle p-5 shadow-md flex-1">
      <p className={`font-data text-micro font-bold uppercase tracking-[2px] mb-2 ${accentClass}`}>
        {t(zoneKey)}
      </p>
      <h4 className="font-display text-[18px] font-semibold text-text-primary mb-1.5">
        {t(titleKey)}
      </h4>
      <p className="font-body text-small text-text-secondary leading-snug">
        {t(bodyKey)}
      </p>
    </div>
  );
}

export function AboutScreen() {
  const t = useT();

  return (
    <PageContainer variant="centered" testId="screen-about" className="pt-24 pb-32">
      <div className="flex flex-col gap-12">
        <motion.header
          className="flex flex-col gap-3"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={springs.smooth}
        >
          <p className="font-data text-micro uppercase tracking-[2px] text-text-muted">
            {t("about.header.kicker")}
          </p>
          <h1 className="font-display text-display text-text-primary leading-tight">
            {t("about.header.headline")}
          </h1>
          <p className="font-body text-body-lg text-text-secondary">
            {t("about.header.subhead")}
          </p>
        </motion.header>

        <motion.section
          className="flex flex-col gap-3"
          aria-labelledby="about-why-title"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springs.smooth, delay: 0.1 }}
        >
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-info">
            {t("about.why.eyebrow")}
          </p>
          <h2 id="about-why-title" className="font-display text-heading text-text-primary">
            {t("about.why.title")}
          </h2>
          <p className="font-body text-body text-text-secondary leading-relaxed">
            {t("about.why.body")}
          </p>
        </motion.section>

        <motion.section
          className="flex flex-col gap-3"
          aria-labelledby="about-pipeline-title"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...springs.smooth, delay: 0.18 }}
        >
          <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-thrive">
            {t("about.pipeline.eyebrow")}
          </p>
          <h2 id="about-pipeline-title" className="font-display text-heading text-text-primary">
            {t("about.pipeline.title")}
          </h2>
          <p className="font-body text-body text-text-secondary leading-relaxed">
            {t("about.pipeline.body")}
          </p>

          <div className="grid grid-cols-1 tablet:grid-cols-3 gap-3 mt-4">
            <PipelineStep
              zoneKey="about.pipeline.bronze.zone"
              accentClass="text-accent-alert"
              titleKey="about.pipeline.bronze.title"
              bodyKey="about.pipeline.bronze.body"
            />
            <PipelineStep
              zoneKey="about.pipeline.silver.zone"
              accentClass="text-text-secondary"
              titleKey="about.pipeline.silver.title"
              bodyKey="about.pipeline.silver.body"
            />
            <PipelineStep
              zoneKey="about.pipeline.gold.zone"
              accentClass="text-accent-caution"
              titleKey="about.pipeline.gold.title"
              bodyKey="about.pipeline.gold.body"
            />
          </div>
        </motion.section>

        <section className="flex flex-col gap-3" aria-labelledby="about-receipts-title">
          <div className="flex items-baseline justify-between gap-4 flex-wrap">
            <div>
              <p className="font-data text-micro font-bold uppercase tracking-[2px] text-accent-insight">
                {t("about.receipts.eyebrow")}
              </p>
              <h2 id="about-receipts-title" className="font-display text-heading text-text-primary">
                {t("about.receipts.title")}
              </h2>
            </div>
            <p className="font-data text-data-sm text-text-muted">
              <span className="text-text-primary font-bold">11</span>{" "}
              {t("about.receipts.dataSources")}
              {" · "}
              <span className="text-text-primary font-bold">1</span>{" "}
              {t("about.receipts.modelLayer")}
            </p>
          </div>
          <p className="font-body text-body text-text-secondary leading-relaxed">
            {t("about.receipts.body")}
          </p>

          <motion.div
            className="grid grid-cols-1 tablet:grid-cols-2 gap-5 mt-6"
            variants={staggerContainer(0.1, stagger.normal)}
            initial="hidden"
            animate="visible"
            data-testid="about-source-grid"
          >
            {SOURCES.map((s) => (
              <motion.div key={s.id} variants={staggerItem}>
                <SourceCard
                  testId={`source-card-${s.id}`}
                  variant={s.variant}
                  titleKey={s.titleKey}
                  publisherKey={s.publisherKey}
                  vintage={s.vintage}
                  blurbKey={s.blurbKey}
                  caveatKey={s.caveatKey}
                  displayUrl={s.displayUrl}
                  href={s.href}
                />
              </motion.div>
            ))}
          </motion.div>
        </section>

      </div>
    </PageContainer>
  );
}
