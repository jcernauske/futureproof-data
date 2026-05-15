import type { CompareBuild } from "@/api/menu";
import { useT } from "@/i18n/useT";

type T = (key: string, vars?: Record<string, string | number>) => string;

interface CompareCostBreakdownProps {
  builds: CompareBuild[];
  highlightIndex: number | null;
}

function fmt(val: number | null): string {
  if (val == null) return "—";
  return val.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function controlLabel(t: T, build: CompareBuild): string {
  if (build.is_out_of_state) return t("compare.cost.controlOutOfState");
  if (build.institution_control?.toLowerCase().includes("private")) return t("compare.cost.controlPrivate");
  return t("compare.cost.controlInState");
}

const COST_ROW_KEYS: { labelKey: string; key: keyof CompareBuild; emphasize?: "alert" | "thrive" }[] = [
  { labelKey: "compare.cost.row.tuition", key: "tuition_annual" },
  { labelKey: "compare.cost.row.roomBoard", key: "room_board_on_campus" },
  { labelKey: "compare.cost.row.coaAnnual", key: "cost_of_attendance_annual" },
  { labelKey: "compare.cost.row.coa4yr", key: "published_cost_4yr", emphasize: "alert" },
  { labelKey: "compare.cost.row.netPrice", key: "net_price_annual", emphasize: "thrive" },
  { labelKey: "compare.cost.row.totalDebt", key: "modeled_total_debt" },
];

export function CompareCostBreakdown({ builds, highlightIndex }: CompareCostBreakdownProps) {
  const t = useT();
  const maxSticker = Math.max(...builds.map((b) => b.published_cost_4yr ?? 0), 1);

  return (
    <div className="flex flex-col gap-0">
      {/* Zone 1: Sticker vs average after-aid cost bars */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted">
            {t("compare.cost.stickerVsAfterAid")}
          </p>
          <p className="max-w-[720px] font-body text-small leading-relaxed text-text-secondary">
            {t("compare.cost.stickerVsAfterAidBody")}
          </p>
        </div>

        {builds.map((build, idx) => {
          const dimmed = highlightIndex !== null && highlightIndex !== idx;
          const hasCost = build.published_cost_4yr != null || build.net_price_annual != null;
          const stickerPct = build.published_cost_4yr != null ? (build.published_cost_4yr / maxSticker) * 100 : 0;
          const net4yr = build.net_price_annual != null ? build.net_price_annual * 4 : null;
          const netPct = net4yr != null ? (net4yr / maxSticker) * 100 : 0;

          return (
            <div
              key={build.build_id}
              data-col={idx + 1}
              className="transition-opacity duration-200"
              style={{ opacity: dimmed ? 0.2 : 1 }}
            >
              <p className="font-body text-[11px] font-bold uppercase tracking-widest text-text-muted mb-1.5">
                {build.school_name}{" "}
                <span className="font-data text-data-sm text-text-muted normal-case font-normal">
                  ({controlLabel(t, build)})
                </span>
              </p>

              {hasCost ? (
                <div className="flex flex-col gap-1.5">
                  {build.published_cost_4yr != null && (
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2.5 rounded-full bg-white/[0.04] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-200"
                          style={{ width: `${stickerPct}%`, background: "rgba(244, 169, 126, 0.30)" }}
                        />
                      </div>
                      <span className="font-data text-data-sm text-accent-alert whitespace-nowrap min-w-[80px] text-right">
                        {fmt(build.published_cost_4yr)}
                      </span>
                    </div>
                  )}
                  {net4yr != null && (
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2.5 rounded-full bg-white/[0.04] overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-200"
                          style={{ width: `${netPct}%`, background: "rgba(125, 212, 163, 0.35)" }}
                        />
                      </div>
                      <span className="font-data text-data-sm text-accent-thrive whitespace-nowrap min-w-[80px] text-right">
                        {fmt(net4yr)}
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <p className="font-body text-small text-text-muted italic">{t("compare.cost.unavailable")}</p>
              )}
            </div>
          );
        })}

        {/* Legend */}
        <div className="flex items-center gap-4 mt-1">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: "rgba(244, 169, 126, 0.50)" }} />
            <span className="font-data text-data-sm text-text-muted">{t("compare.cost.legend.sticker")}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: "rgba(125, 212, 163, 0.55)" }} />
            <span className="font-data text-data-sm text-text-muted">{t("compare.cost.legend.afterAid")}</span>
          </div>
        </div>
      </div>

      {/* Zone 2: Cost Line-Item Table */}
      <div className="mt-5 pt-4 border-t border-border-subtle">
        <p className="font-data text-[11px] font-bold tracking-widest uppercase text-text-muted mb-3">
          {t("compare.cost.detail")}
        </p>

        {/* Desktop table */}
        <div className="hidden tablet:block">
          <div
            className="grid items-center gap-y-0"
            style={{ gridTemplateColumns: `160px repeat(${builds.length}, 1fr)` }}
          >
            {/* Header */}
            <div />
            {builds.map((build) => (
              <p key={build.build_id} className="font-body text-[11px] font-bold uppercase text-text-muted text-center pb-2">
                {build.school_name}
              </p>
            ))}

            {COST_ROW_KEYS.map((row) => (
              <CostTableRow key={row.key} row={{ ...row, label: t(row.labelKey) }} builds={builds} highlightIndex={highlightIndex} />
            ))}
          </div>
        </div>

        {/* Mobile cards */}
        <div className="tablet:hidden flex flex-col gap-3">
          {builds.map((build, idx) => (
            <div
              key={build.build_id}
              data-col={idx + 1}
              className="bg-bp-mid/50 rounded-xl p-4 border border-border-subtle transition-opacity duration-200"
              style={{ opacity: highlightIndex !== null && highlightIndex !== idx ? 0.2 : 1 }}
            >
              <p className="font-display font-semibold text-[14px] text-text-primary mb-2">
                {build.school_name}
              </p>
              {COST_ROW_KEYS.map((row) => {
                const val = build[row.key] as number | null;
                const colorClass = row.emphasize === "alert" ? "text-accent-alert" : row.emphasize === "thrive" ? "text-accent-thrive" : "text-text-primary";
                return (
                  <div key={row.key} className="flex justify-between py-1.5 border-t border-border-subtle">
                    <span className="font-body text-small text-text-secondary">{t(row.labelKey)}</span>
                    <span className={`font-data text-data ${val == null ? "text-text-muted" : colorClass}`}>
                      {fmt(val)}
                    </span>
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function CostTableRow({
  row,
  builds,
  highlightIndex,
}: {
  row: { label: string; key: keyof CompareBuild; emphasize?: "alert" | "thrive" };
  builds: CompareBuild[];
  highlightIndex: number | null;
}) {
  const isBold = row.emphasize != null;
  const labelClass = isBold ? "font-bold" : "";
  const dataColor = row.emphasize === "alert" ? "text-accent-alert" : row.emphasize === "thrive" ? "text-accent-thrive" : "text-text-primary";

  return (
    <>
      <span className={`font-body text-small text-text-secondary py-2.5 border-t border-border-subtle ${labelClass}`}>
        {row.label}
      </span>
      {builds.map((build, idx) => {
        const val = build[row.key] as number | null;
        const dimmed = highlightIndex !== null && highlightIndex !== idx;
        return (
          <span
            key={build.build_id}
            data-col={idx + 1}
            className={`font-data text-data text-center py-2.5 border-t border-border-subtle transition-opacity duration-200 ${isBold ? "font-bold" : ""} ${val == null ? "text-text-muted" : dataColor}`}
            style={{ opacity: dimmed ? 0.2 : 1 }}
          >
            {fmt(val)}
          </span>
        );
      })}
    </>
  );
}
