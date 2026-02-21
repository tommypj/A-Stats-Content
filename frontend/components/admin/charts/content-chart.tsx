"use client";

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface ContentChartProps {
  data: Array<{ month: string; articles: number; outlines: number; images: number }>;
}

export function ContentChart({ data }: ContentChartProps) {
  return (
    <div className="w-full h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="month"
            stroke="#6b7280"
            fontSize={12}
            tickFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleDateString("en-US", { month: "short" });
            }}
          />
          <YAxis stroke="#6b7280" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#fff",
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
            }}
            labelFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
            }}
          />
          <Legend />
          <Bar dataKey="articles" fill="#3b82f6" name="Articles" />
          <Bar dataKey="outlines" fill="#10b981" name="Outlines" />
          <Bar dataKey="images" fill="#f59e0b" name="Images" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
