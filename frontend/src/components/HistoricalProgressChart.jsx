import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";

export default function HistoricalProgressChart({ data }) {
  if (!data || data.length === 0) {
    return null;
  }

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-slate-200 rounded-lg shadow-lg">
          <p className="font-semibold text-slate-900">{item.label}</p>
          <p className="text-sm text-emerald-700">
            Payés: {item.paid} / {item.total}
          </p>
          <p className="text-sm text-slate-600">
            Taux: {item.percentage}%
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
          <TrendingUp className="w-5 h-5 text-emerald-700" />
          Évolution des paiements
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis 
              dataKey="label" 
              stroke="#64748b"
              style={{ fontSize: "12px", fontFamily: "Manrope" }}
            />
            <YAxis 
              stroke="#64748b"
              style={{ fontSize: "12px", fontFamily: "Manrope" }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="percentage" radius={[8, 8, 0, 0]}>
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.percentage >= 80 ? "#059669" : entry.percentage >= 50 ? "#f59e0b" : "#dc2626"} 
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4 flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-emerald-600"></div>
            <span className="text-slate-600">≥ 80%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-amber-500"></div>
            <span className="text-slate-600">50-79%</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded bg-red-600"></div>
            <span className="text-slate-600">{'<'} 50%</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
