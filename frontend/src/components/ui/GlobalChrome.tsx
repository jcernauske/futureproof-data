const STARS = Array.from({ length: 18 }, (_, i) => ({
  left: `${[10, 75, 4, 90, 92, 12, 96, 55, 42, 6, 50, 38, 22, 68, 84, 30, 60, 18][i]}%`,
  top: `${[6, 12, 30, 18, 65, 78, 55, 88, 4, 55, 40, 72, 22, 48, 8, 92, 34, 82][i]}%`,
  delay: `${[0, 0.7, 1.5, 0.3, 2.0, 1.1, 0.6, 1.8, 2.3, 0.9, 1.3, 2.6, 0.4, 1.9, 2.5, 1.4, 0.2, 2.1][i]}s`,
  duration: `${[3.5, 4.2, 3.8, 5.0, 3.2, 4.5, 3.9, 4.1, 3.6, 4.8, 5.2, 3.4, 4.0, 3.7, 4.6, 5.1, 3.3, 4.3][i]}s`,
}));

export function GlobalChrome() {
  return (
    <>
      <div className="noise-overlay" aria-hidden="true" />
      <div
        className="fixed inset-0 pointer-events-none overflow-hidden -z-10"
        aria-hidden="true"
      >
        <div className="ambient-glow" />
        {STARS.map((star, i) => (
          <div
            key={i}
            className="star"
            style={{
              left: star.left,
              top: star.top,
              animationDelay: star.delay,
              animationDuration: star.duration,
            }}
          />
        ))}
      </div>
    </>
  );
}
