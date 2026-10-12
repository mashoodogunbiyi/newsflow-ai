import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NewsFlow AI - Source-grounded LinkedIn content",
  description:
    "A review-first workspace for turning authorised news facts into professional LinkedIn drafts and original supporting illustrations.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-stone-50 font-sans text-emerald-950">
        {children}
      </body>
    </html>
  );
}
