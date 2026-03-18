import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { TrendingUp, AlertCircle, Clock } from "lucide-react";

const STRUCTURE_COLORS = [
  "#064E3B", // emerald-900
  "#F97316", // orange-500
  "#3B82F6", // blue-500
  "#8B5CF6", // violet-500
  "#14B8A6", // teal-500
  "#EC4899", // pink-500
];

const formatCurrency = (value) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);

const CustomTooltip = ({ active, payload, label, structures }) => {
  if (!active || !payload || !payload.length) return null;
  const total = payload.find(p => p.dataKey === "total");
  return (
    <div className="bg-white p-3 border border-slate-200 rounded-lg shadow-lg text-sm min-w-[160px]">
      <p className="font-semibold text-slate-900 mb-2">{label}</p>
      {payload
        .filter(p => p.dataKey !== "total" && p.value > 0)
        .map((p, i) => (
          <div key={i} className="flex justify-between gap-4">
            <span style={{ color: p.fill }}>{p.name}</span>
            <span className="font-medium text-slate-800">{formatCurrency(p.value)}</span>
          </div>
        ))}
      {total && (
        <div className="flex justify-between gap-4 mt-2 pt-2 border-t border-slate-100">
          <span className="text-slate-500">Total</span>
          <span className="font-bold text-slate-900">{formatCurrency(total.value)}</span>
        </div>
      )}
    </div>
  );
};

export default function CashflowChart({ history, structures, lateTenants }) {
  if (!history || history.length === 0) return null;

  return (
    <div className="space-y-6">
      {/* Cashflow Chart */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
            <TrendingUp className="w-5 h-5 text-emerald-700" />
            Virements reçus par structure (6 mois)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={320}>
            <ComposedChart data={history} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="label"
                stroke="#94a3b8"
                tick={{ fontSize: 12, fontFamily: "Manrope", fill: "#64748b" }}
              />
              <YAxis
                stroke="#94a3b8"
                tick={{ fontSize: 11, fontFamily: "Manrope", fill: "#64748b" }}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k€`}
              />
              <Tooltip content={<CustomTooltip structures={structures} />} />
              <Legend
                wrapperStyle={{ fontSize: "12px", fontFamily: "Manrope", paddingTop: "16px" }}
              />
              {structures.map((struct, idx) => (
                <Bar
                  key={struct}
                  dataKey={struct}
                  name={struct}
                  stackId="a"
                  fill={STRUCTURE_COLORS[idx % STRUCTURE_COLORS.length]}
                  radius={idx === structures.length - 1 ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                />
              ))}
              <Line
                type="monotone"
                dataKey="total"
                name="Total"
                stroke="#1e293b"
                strokeWidth={2}
                dot={{ fill: "#1e293b", r: 4 }}
                activeDot={{ r: 6 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Late Tenants */}
      {lateTenants && lateTenants.length > 0 && (
        <Card className="border-orange-200">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="flex items-center gap-2 text-orange-800" style={{ fontFamily: "Manrope" }}>
              <AlertCircle className="w-5 h-5 text-orange-500" />
              Retards de paiement ({lateTenants.length})
            </CardTitle>
            <Link
              to="/tenants"
              className="text-sm text-orange-600 hover:text-orange-800 font-medium"
            >
              Voir tous →
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100">
              {lateTenants.map((tenant) => (
                <Link
                  key={tenant.id}
                  to={`/tenants/${tenant.id}`}
                  className="flex items-center justify-between px-6 py-3 hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold
                      ${tenant.months_late >= 2 ? "bg-red-100 text-red-700" : "bg-orange-100 text-orange-700"}`}>
                      {tenant.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="font-medium text-slate-900 text-sm">{tenant.name}</p>
                      <p className="text-xs text-slate-500">{tenant.structure}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-right">
                    <p className="font-semibold text-slate-800 text-sm" style={{ fontFamily: "Manrope" }}>
                      {formatCurrency(tenant.rent_amount)}
                    </p>
                    <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-semibold
                      ${tenant.months_late >= 2 ? "bg-red-100 text-red-700" : "bg-orange-100 text-orange-700"}`}>
                      <Clock className="w-3 h-3" />
                      {tenant.months_late === 0
                        ? "Ce mois"
                        : `${tenant.months_late + 1} mois`}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
