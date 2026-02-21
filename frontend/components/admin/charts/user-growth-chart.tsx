"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface UserGrowthChartProps {
  data: Array<{ month: string; count: number }>;
}

export function UserGrowthChart({ data }: UserGrowthChartProps) {
  return (
    <div className="w-full h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="month"
            stroke="#6b7280"
            fontSize={12}
            tickFormatter={(value) => {
              const date = new Date(value);
              return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
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
          <Line
            type="monotone"
            dataKey="count"
            stroke="#627862"
            strokeWidth={2}
            name="Users"
            dot={{ fill: "#627862", r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
