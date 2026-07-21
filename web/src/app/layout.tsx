import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "dtp-tunes",
  description: "Self-hosted music streaming, your library, your rules.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0a0a0c",
};

// Runs before hydration so the chosen accent applies without a color flash.
// Keep the key and tone list in sync with src/lib/accent.ts.
const accentInitScript = `(function () {
  try {
    var tone = localStorage.getItem("dtp-tunes-accent");
    var valid = ["pink", "green", "blue", "purple", "orange"];
    document.documentElement.dataset.accent = valid.indexOf(tone) >= 0 ? tone : "pink";
  } catch (e) {
    document.documentElement.dataset.accent = "pink";
  }
})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: accentInitScript }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
