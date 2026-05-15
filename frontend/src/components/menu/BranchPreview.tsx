import type { CompareBranchBuild } from "@/api/menu";
import { useT } from "@/i18n/useT";

interface BranchPreviewProps {
  branches: CompareBranchBuild[];
  buildColors: string[];
  highlightIndex?: number | null;
}

export function BranchPreview({ branches, buildColors, highlightIndex = null }: BranchPreviewProps) {
  const t = useT();
  const allSocs = new Map<string, string[]>();
  for (const branch of branches) {
    for (const dest of branch.destinations) {
      const list = allSocs.get(dest.to_soc) ?? [];
      list.push(branch.build_id);
      allSocs.set(dest.to_soc, list);
    }
  }

  return (
    <div className="grid grid-cols-1 tablet:grid-cols-2 desktop:grid-cols-4 gap-3">
      {branches.map((branch, idx) => {
        const color = buildColors[idx] ?? buildColors[0]!;
        return (
          <article
            key={branch.build_id}
            data-col={idx + 1}
            data-testid={`card-branch-${branch.build_id}`}
            aria-label={t("compare.branches.cardAriaLabel", { career: branch.career, n: branch.destinations.length })}
            className="bg-bp-mid border border-border-subtle rounded-xl p-5 relative overflow-hidden transition-opacity duration-200"
            style={{ opacity: highlightIndex !== null && highlightIndex !== idx ? 0.2 : 1 }}
          >
            <div
              className="absolute left-0 top-0 bottom-0 w-1 rounded-l-xl"
              style={{ background: `linear-gradient(180deg, ${color}, transparent)` }}
            />

            <p className="font-display font-semibold text-sm mb-3" style={{ color }}>
              {branch.career}
            </p>

            {branch.destinations.map((dest, di) => {
              const sharedWith = (allSocs.get(dest.to_soc) ?? []).filter(
                (id) => id !== branch.build_id,
              );
              return (
                <div
                  key={di}
                  className={`flex items-center gap-2 py-2 ${
                    di < branch.destinations.length - 1 ? "border-b border-border-subtle" : ""
                  }`}
                >
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: color, boxShadow: `0 0 8px color-mix(in srgb, ${color} 30%, transparent)` }}
                  />
                  <span className="text-sm font-semibold text-text-primary">
                    {dest.to_title}
                  </span>
                  {sharedWith.length > 0 && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold tracking-wider uppercase text-accent-insight bg-accent-insight/10 px-2 py-0.5 rounded-full ml-auto shrink-0">
                      ↔ {sharedWith.map((id) => {
                        const branchData = branches.find((b) => b.build_id === id);
                        return branchData?.career.split(" ")[0] ?? id;
                      }).join(", ")}
                    </span>
                  )}
                </div>
              );
            })}

            {branch.destinations.length === 0 && (
              <p className="text-sm text-text-muted italic">{t("compare.branches.empty")}</p>
            )}
          </article>
        );
      })}
    </div>
  );
}
