"use client";

/**
 * No React state: the active theme lives on <html data-theme>, and CSS decides
 * which label to show. That keeps the server and client markup identical, so
 * there is no hydration mismatch and no flash of the wrong label.
 */
export function ThemeToggle() {
  function toggle() {
    const root = document.documentElement;
    const current =
      root.dataset.theme ??
      (window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light");
    const next = current === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try {
      localStorage.setItem("faultline-theme", next);
    } catch {
      // Private browsing: the choice just will not persist.
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label="Switch colour mode"
      className="eyebrow text-ink-faint hover:text-ink transition-colors cursor-pointer"
    >
      <span className="when-light">Dark</span>
      <span className="when-dark">Light</span>
    </button>
  );
}
