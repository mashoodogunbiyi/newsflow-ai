import Link from "next/link";

import { buttonStyles } from "@/components/ui/button";

type ArticleSelectionProps = {
  articleId: string;
  className?: string;
  label?: string;
};

export function ArticleSelection({
  articleId,
  className = "",
  label = "Select article",
}: ArticleSelectionProps) {
  return (
    <Link
      className={`${buttonStyles("primary")} ${className}`}
      href={`/generate?articleId=${encodeURIComponent(articleId)}`}
      prefetch={false}
    >
      {label}
    </Link>
  );
}
