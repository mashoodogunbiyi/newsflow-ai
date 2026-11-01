import { ArticleCard } from "@/components/articles/article-card";
import type { Article } from "@/types/article";

export function ArticleGrid({ articles }: { articles: Article[] }) {
  return (
    <ul className="grid gap-5 md:grid-cols-2 xl:grid-cols-3" role="list">
      {articles.map((article) => (
        <li className="min-w-0" key={article.id}>
          <ArticleCard article={article} />
        </li>
      ))}
    </ul>
  );
}
