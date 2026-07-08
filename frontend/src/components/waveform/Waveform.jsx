/**
 * Waveform — the signature visual element of the app.
 *
 * States:
 *   idle       → gentle breathing animation (bars subtly pulsing)
 *   recording  → bars animate with more energy/height
 *   populated  → static bars representing actual audio amplitude
 *
 * Used in: hero, upload dropzone, score overlay
 */
export function Waveform({ state = "idle", bars = 40, className = "" }) {
  return (
    <div
      className={`flex items-end justify-center gap-[2px] h-full ${className}`}
      aria-hidden="true"
    >
      {Array.from({ length: bars }).map((_, i) => {
        const baseHeight = getBarHeight(i, bars, state);
        const delay = `${(i * 60) % 1000}ms`;

        return (
          <div
            key={i}
            className={`rounded-full transition-all duration-500 ${getBarColor(state)}`}
            style={{
              width: "3px",
              height: `${baseHeight}%`,
              animationDelay: delay,
              animation: state === "idle"
                ? `breathe 2.5s ease-in-out ${delay} infinite`
                : state === "recording"
                ? `breathe 0.8s ease-in-out ${delay} infinite`
                : "none",
            }}
          />
        );
      })}
    </div>
  );
}

function getBarHeight(index, total, state) {
  const center = total / 2;
  const distFromCenter = Math.abs(index - center) / center;

  if (state === "idle") {
    // Smooth bell curve
    return 20 + (1 - distFromCenter * distFromCenter) * 50;
  }
  if (state === "recording") {
    // More dynamic, taller
    return 25 + (1 - distFromCenter) * 65;
  }
  // populated: use a pseudo-random pattern based on index
  const hash = Math.sin(index * 12.9898) * 43758.5453;
  const pseudo = hash - Math.floor(hash);
  return 15 + pseudo * 70;
}

function getBarColor(state) {
  if (state === "recording") return "bg-danger";
  if (state === "populated") return "bg-primary/60";
  return "bg-card-border";
}
