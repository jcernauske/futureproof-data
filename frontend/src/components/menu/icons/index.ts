/**
 * Per-tool icon registry for `<GemmaTrace>`. The icon `id` strings here
 * match the `icon` field on `TOOL_LABEL_MAP` entries in
 * `frontend/src/components/menu/toolLabels.ts`.
 */

import { IconBranch } from "./IconBranch";
import { IconBriefcaseStack } from "./IconBriefcaseStack";
import { IconCareerCompass } from "./IconCareerCompass";
import { IconMapPin } from "./IconMapPin";
import { IconMortarboard } from "./IconMortarboard";
import { IconScale } from "./IconScale";
import { IconWrench } from "./IconWrench";

export {
  IconBranch,
  IconBriefcaseStack,
  IconCareerCompass,
  IconMapPin,
  IconMortarboard,
  IconScale,
  IconWrench,
};

interface IconProps {
  size?: number;
  className?: string;
}

type IconComponent = (props: IconProps) => React.ReactNode;

export const TRACE_ICONS: Record<string, IconComponent> = {
  IconCareerCompass,
  IconBriefcaseStack,
  IconMapPin,
  IconScale,
  IconBranch,
  IconMortarboard,
  IconWrench,
};

/** Resolve an icon id to its React component. Falls back to
 *  `IconWrench` for unknown ids — matches the unknown-tool default
 *  label behavior. */
export function resolveTraceIcon(iconId: string): IconComponent {
  return TRACE_ICONS[iconId] ?? IconWrench;
}
