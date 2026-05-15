import {
  Component,
  type ErrorInfo,
  type ReactElement,
  type ReactNode,
} from "react";
import { useT } from "@/i18n/useT";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error("[ErrorBoundary]", error, info.componentStack);
    }
  }

  render(): ReactNode {
    if (this.state.error) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}

function ErrorFallback({ error }: { error: Error }): ReactElement {
  // Inline Brightpath tokens only — no design-system imports, no router.
  // The profileStore is a tiny in-memory store; if it's the crash source
  // the error text degrades to English (default locale) which is fine.
  const t = useT();
  const isDev = import.meta.env.DEV;
  const stack = (error.stack ?? error.message ?? "").slice(0, 2048);

  const handleRefresh = () => {
    window.location.reload();
  };

  const handleHome = () => {
    window.location.href = "/";
  };

  return (
    <div
      role="alert"
      aria-live="assertive"
      data-testid="error-boundary-fallback"
      className="min-h-screen w-full flex items-center justify-center bg-bp-deep p-6"
    >
      <div className="max-w-md w-full bg-bp-mid rounded-xl p-8 border border-border-subtle">
        <h1 className="text-heading font-display text-text-primary mb-3">
          {t("error.heading")}
        </h1>
        <p className="text-body-sm text-text-secondary mb-2">
          {t("error.body1")}
        </p>
        <p className="text-body-sm text-text-secondary mb-6">
          {t("error.body2")}
        </p>
        <div className="flex gap-3 mb-4">
          <button
            type="button"
            data-testid="error-boundary-refresh"
            aria-label={t("error.refreshAria")}
            autoFocus
            onClick={handleRefresh}
            className="rounded-lg font-body bg-accent-thrive text-text-inverse font-bold text-cta h-12 px-7 cursor-pointer"
          >
            {t("error.refresh")}
          </button>
          <button
            type="button"
            data-testid="error-boundary-home"
            aria-label={t("error.homeAria")}
            onClick={handleHome}
            className="rounded-lg font-body bg-transparent text-accent-info border border-accent-info h-12 px-6 text-body-sm cursor-pointer"
          >
            {t("error.home")}
          </button>
        </div>
        {isDev ? (
          <details
            data-testid="error-boundary-details"
            aria-label={t("error.detailsAria")}
            className="text-text-muted text-small"
          >
            <summary className="cursor-pointer">{t("error.detailsSummary")}</summary>
            <pre className="mt-2 whitespace-pre-wrap break-words text-xs font-mono">
              {stack}
            </pre>
          </details>
        ) : null}
      </div>
    </div>
  );
}
