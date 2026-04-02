"use client";

import type { ProductComparisonData } from "@/types";

interface ProductComparisonCardProps {
  data: ProductComparisonData;
}

export function ProductComparisonCard({ data }: ProductComparisonCardProps) {
  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-blue-500">
        Container Comparison
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        {data.products.map((product) => (
          <div
            key={product.name}
            className="rounded-lg border border-blue-200 bg-white p-3 text-center shadow-sm"
          >
            <p className="text-sm font-bold text-gray-800">{product.name}</p>
            <p className="mt-1 text-lg font-extrabold text-blue-600">{product.price}</p>
            <p className="mt-1 text-xs text-gray-500">{product.size}</p>
            {product.capacity && (
              <p className="text-xs text-gray-400">{product.capacity}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
