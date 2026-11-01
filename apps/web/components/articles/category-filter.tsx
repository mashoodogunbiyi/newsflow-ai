import { ARTICLE_CATEGORIES, type ArticleCategory } from "@/types/article";

type CategoryFilterProps = {
  selectedCategory?: ArticleCategory;
};

export function CategoryFilter({ selectedCategory }: CategoryFilterProps) {
  return (
    <div>
      <label className="text-sm font-semibold text-emerald-950" htmlFor="article-category">
        Category
      </label>
      <select
        className="mt-2 min-h-11 w-full rounded-2xl border border-emerald-950/15 bg-white px-4 py-2.5 text-sm text-emerald-950 outline-none transition focus:border-emerald-700 focus:ring-2 focus:ring-emerald-700/15"
        defaultValue={selectedCategory ?? ""}
        id="article-category"
        name="category"
      >
        <option value="">All categories</option>
        {ARTICLE_CATEGORIES.map((category) => (
          <option key={category.id} value={category.id}>
            {category.label}
          </option>
        ))}
      </select>
    </div>
  );
}
