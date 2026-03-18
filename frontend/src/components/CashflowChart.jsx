import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { TrendingUp, AlertCircle, Clock } from "lucide-react";

const formatCurrency = (value) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(value);

function getBarColor(pct) {
  if (pct >= 80) return "bg-emerald-600";
  if (pct >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function getTextColor(pct) {
  if (pct >= 80) return "text-emerald-700";
  if (pct >= 50) return "text-amber-600";
  return "text-red-600";
}

export default function CashflowChart({ history, lateTenants }) {
  return (
    <div className="space-y-6">
      {/* Monthly progress bars */}
      {history && history.length > 0 && (
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
              <TrendingUp className="w-5 h-5 text-emerald-700" />
              Évolution des paiements (6 mois)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {history.map((month, idx) => (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-700 w-16">{month.label}</span>
                  <span className="text-slate-500 text-xs">
                    {month.paid} / {month.total} locataires
                  </span>
                  <span className={`font-bold w-12 text-right ${getTextColor(month.percentage)}`} style={{ fontFamily: "Manrope" }}>
                    {month.percentage}%
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-5">
                  <div
                    className={`h-5 rounded-full transition-all duration-500 flex items-center justify-end pr-2 ${getBarColor(month.percentage)}`}
                    style={{ width: `${Math.max(month.percentage, 2)}%` }}
                  >
                    {month.percentage > 15 && (
                      <span className="text-white text-xs font-semibold">{month.percentage}%</span>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Legend */}
            <div className="flex items-center justify-center gap-6 pt-2 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-emerald-600 inline-block" /> ≥ 80%
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-amber-500 inline-block" /> 50–79%
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> &lt; 50%
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Late tenants */}
      {lateTenants && lateTenants.length > 0 && (
        <Card className="border-orange-200">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="flex items-center gap-2 text-orange-800" style={{ fontFamily: "Manrope" }}>
              <AlertCircle className="w-5 h-5 text-orange-500" />
              Retards de paiement ({lateTenants.length})
            </CardTitle>
            <Link to="/tenants" className="text-sm text-orange-600 hover:text-orange-800 font-medium">
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
                      {tenant.months_late === 0 ? "Ce mois" : `${tenant.months_late + 1} mois`}
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
