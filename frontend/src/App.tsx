import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { springs } from "@/styles/motion";
import { API_BASE_URL } from "@/lib/api";

const ACCENT_COLORS = [
  { name: "thrive", class: "bg-accent-thrive" },
  { name: "alert", class: "bg-accent-alert" },
  { name: "caution", class: "bg-accent-caution" },
  { name: "insight", class: "bg-accent-insight" },
  { name: "info", class: "bg-accent-info" },
  { name: "empathy", class: "bg-accent-empathy" },
] as const;

function App() {
  const [apiStatus, setApiStatus] = useState<"loading" | "connected" | "disconnected">("loading");

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => {
        if (res.ok) setApiStatus("connected");
        else setApiStatus("disconnected");
      })
      .catch(() => setApiStatus("disconnected"));
  }, []);

  return (
    <div className="min-h-screen bg-bp-void">
      <main
        className="mx-auto max-w-[800px] px-6 py-16 bg-bp-deep min-h-screen"
        aria-label="FutureProof design system shell"
      >
        <h1 className="font-display text-hero text-text-primary font-semibold mb-4">
          FutureProof
        </h1>

        <p className="font-body text-body text-text-secondary mb-2">
          A college degree isn't a destination.
        </p>
        <p className="font-body text-body text-text-primary font-bold mb-8">
          It's a starting position.
        </p>

        <p className="font-data text-data-lg text-accent-caution mb-10">
          $48,200
        </p>

        <div className="flex gap-4 mb-10">
          {ACCENT_COLORS.map((color) => (
            <div key={color.name} className="flex flex-col items-center gap-2">
              <div className={`w-10 h-10 rounded-full ${color.class}`} />
              <span className="font-data text-micro text-text-muted">
                {color.name}
              </span>
            </div>
          ))}
        </div>

        <motion.div
          className="bg-bp-surface rounded-xl p-8 mb-10"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={springs.bouncy}
        >
          <p className="font-body text-body text-text-primary">
            Design system active
          </p>
        </motion.div>

        <div
          className="flex items-center gap-2"
          role="status"
          aria-label="Backend API connection status"
        >
          <div
            className={`w-3 h-3 rounded-full ${
              apiStatus === "connected"
                ? "bg-accent-thrive"
                : apiStatus === "disconnected"
                  ? "bg-accent-alert"
                  : "bg-text-muted"
            }`}
          />
          <span className="font-body text-small text-text-secondary">
            API Status:{" "}
            {apiStatus === "connected"
              ? "Connected"
              : apiStatus === "disconnected"
                ? "Disconnected"
                : "Checking..."}
          </span>
        </div>
      </main>
    </div>
  );
}

export default App;
