import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Users, Building2, ChevronDown, ChevronUp, CalendarDays } from "lucide-react";

const ASSOCIE_COLORS = {
  Gaetan:  { bg: "bg-violet-50",  border: "border-violet-200", text: "text-violet-700",  badge: "bg-violet-100 text-violet-800",  bar: "bg-violet-500" },
  Romain:  { bg: "bg-sky-50",     border: "border-sky-200",    text: "text-sky-700",     badge: "bg-sky-100 text-sky-800",        bar: "bg-sky-500" },
  Clément: { bg: "bg-amber-50",   border: "border-amber-200",  text: "text-amber-700",   badge: "bg-amber-100 text-amber-800",    bar: "bg-amber-500" },
};

const ASSOCIE_CELL_COLORS = {
  Gaetan:  { pos: "text-violet-600 font-semibold", neg: "text-red-500", zero: "text-slate-300" },
  Romain:  { pos: "text-sky-600 font-semibold",    neg: "text-red-500", zero: "text-slate-300" },
  Clément: { pos: "text-amber-600 font-semibold",  neg: "text-red-500", zero: "text-slate-300" },
};

const fmt = (n) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(n);

function StructureCashflowCard({ data }) {
  const isPositive = data.cashflow >= 0;
  return (
    <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-800 text-sm">{data.structure}</h4>
        <span className={`text-base font-bold ${isPositive ? "text-emerald-600" : "text-red-500"}`}>
          {isPositive ? "+" : ""}{fmt(data.cashflow)}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5 p-2 bg-emerald-50 rounded-lg">
          <TrendingUp className="w-3 h-3 text-emerald-600 shrink-0" />
          <div>
            <p className="text-slate-500">Loyers</p>
            <p className="font-semibold text-emerald-700">{fmt(data.loyers)}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 p-2 bg-red-50 rounded-lg">
          <TrendingDown className="w-3 h-3 text-red-500 shrink-0" />
          <div>
            <p className="text-slate-500">Dépenses</p>
            <p className="font-semibold text-red-600">{fmt(data.depenses)}</p>
          </div>
        </div>
      </div>
      {data.loyers > 0 && (
        <div>
          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div
              className={`h-2 rounded-full ${isPositive ? "bg-emerald-400" : "bg-red-400"}`}
              style={{ width: `${Math.min(100, Math.max(0, (data.cashflow / data.loyers) * 100))}%` }}
            />
          </div>
          <p className="text-xs text-slate-400 mt-1">{data.transactions} transaction(s)</p>
        </div>
      )}
    </div>
  );
}

function AssocieCard({ data }) {
  const [expanded, setExpanded] = useState(false);
  const colors = ASSOCIE_COLORS[data.nom] || ASSOCIE_COLORS.Gaetan;
  const isPositive = data.total >= 0;

  return (
    <div className={`rounded-xl border ${colors.border} ${colors.bg} overflow-hidden`}>
      <button
        className="w-full p-4 flex items-center justify-between"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white ${colors.bar}`}>
            {data.nom[0]}
          </div>
          <div className="text-left">
            <p className={`font-bold text-base ${colors.text}`}>{data.nom}</p>
            <p className="text-xs text-slate-500">Cashflow mensuel · Annuel depuis jan.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className={`font-bold text-lg ${isPositive ? "text-emerald-600" : "text-red-500"}`}>
              {isPositive ? "+" : ""}{fmt(data.total)}
            </p>
            <p className="text-xs text-slate-400">Annuel : {fmt(data.annuel)}</p>
          </div>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-2 border-t border-slate-200">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider pt-3 pb-1">
            Répartition par structure
          </p>
          {data.detail.filter(d => d.part_pct > 0).map((d, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-slate-100 last:border-0">
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-700">{d.structure}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${colors.badge}`}>
                  {d.part_pct}%
                </span>
              </div>
              <div className="text-right">
                <p className={`text-sm font-semibold ${d.montant >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                  {d.montant >= 0 ? "+" : ""}{fmt(d.montant)}
                </p>
                <p className="text-xs text-slate-400">{fmt(d.cashflow_structure)} total</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MonthlyAssociesTable({ associes, monthly }) {
  if (!monthly || monthly.length === 0) return null;

  // Calcul du total par mois (somme des 3 associés)
  const totauxMensuels = monthly.map((m, idx) => {
    const sum = associes.reduce((acc, a) => {
      const mData = a.monthly?.[idx];
      return acc + (mData?.cashflow || 0);
    }, 0);
    return { label: m.label, total: sum };
  });

  // Total annuel par associé
  const totalAnnuel = associes.reduce((acc, a) => {
    acc[a.nom] = a.annuel;
    return acc;
  }, {});

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
          <CalendarDays className="w-5 h-5 text-slate-700" />
          Rapport mensuel par associé
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 pr-4 text-xs font-semibold text-slate-500 uppercase tracking-wider w-20">Mois</th>
                {associes.map(a => {
                  const colors = ASSOCIE_COLORS[a.nom] || ASSOCIE_COLORS.Gaetan;
                  return (
                    <th key={a.nom} className="text-right py-2 px-3">
                      <div className="flex items-center justify-end gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${colors.bar}`} />
                        <span className={`text-xs font-semibold ${colors.text}`}>{a.nom}</span>
                      </div>
                    </th>
                  );
                })}
                <th className="text-right py-2 pl-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Total</th>
              </tr>
            </thead>
            <tbody>
              {monthly.map((m, idx) => {
                const rowTotal = totauxMensuels[idx].total;
                return (
                  <tr key={idx} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 pr-4 text-xs font-semibold text-slate-600 uppercase">{m.label}</td>
                    {associes.map(a => {
                      const mData = a.monthly?.[idx];
                      const val = mData?.cashflow || 0;
                      const cellColors = ASSOCIE_CELL_COLORS[a.nom] || ASSOCIE_CELL_COLORS.Gaetan;
                      const cls = val > 0 ? cellColors.pos : val < 0 ? cellColors.neg : cellColors.zero;
                      return (
                        <td key={a.nom} className={`text-right py-2.5 px-3 text-sm tabular-nums ${cls}`}>
                          {val === 0 ? "—" : `${val > 0 ? "+" : ""}${fmt(val)}`}
                        </td>
                      );
                    })}
                    <td className={`text-right py-2.5 pl-3 text-sm font-bold tabular-nums ${rowTotal >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                      {rowTotal === 0 ? "—" : `${rowTotal > 0 ? "+" : ""}${fmt(rowTotal)}`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-200 bg-slate-50">
                <td className="py-3 pr-4 text-xs font-bold text-slate-700 uppercase">Total</td>
                {associes.map(a => {
                  const val = totalAnnuel[a.nom] || 0;
                  const colors = ASSOCIE_COLORS[a.nom] || ASSOCIE_COLORS.Gaetan;
                  return (
                    <td key={a.nom} className={`text-right py-3 px-3 text-sm font-bold tabular-nums ${val >= 0 ? colors.text : "text-red-500"}`}>
                      {val === 0 ? "—" : `${val > 0 ? "+" : ""}${fmt(val)}`}
                    </td>
                  );
                })}
                <td className={`text-right py-3 pl-3 text-sm font-bold tabular-nums ${
                  associes.reduce((s, a) => s + (a.annuel || 0), 0) >= 0 ? "text-emerald-600" : "text-red-500"
                }`}>
                  {`${associes.reduce((s, a) => s + (a.annuel || 0), 0) >= 0 ? "+" : ""}${fmt(associes.reduce((s, a) => s + (a.annuel || 0), 0))}`}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AssociesCashflow({ data }) {
  if (!data) return null;

  const { structures = [], total = {}, associes = [], monthly = [], period, oldest_transaction } = data;

  return (
    <div className="space-y-6">
      {/* Cashflow par structure */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
            <Building2 className="w-5 h-5 text-slate-700" />
            Cashflow par structure
            <span className="text-xs font-normal text-slate-400 ml-auto">
              {period} · données depuis {oldest_transaction}
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Total global */}
          <div className="grid grid-cols-3 gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="text-center">
              <p className="text-xs text-slate-500 mb-1">Loyers encaissés</p>
              <p className="text-lg font-bold text-emerald-600" style={{ fontFamily: "Manrope" }}>
                {fmt(total.loyers)}
              </p>
            </div>
            <div className="text-center border-x border-slate-200">
              <p className="text-xs text-slate-500 mb-1">Dépenses</p>
              <p className="text-lg font-bold text-red-500" style={{ fontFamily: "Manrope" }}>
                -{fmt(total.depenses)}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-slate-500 mb-1">Cashflow net</p>
              <p className={`text-lg font-bold ${total.cashflow >= 0 ? "text-emerald-600" : "text-red-500"}`} style={{ fontFamily: "Manrope" }}>
                {total.cashflow >= 0 ? "+" : ""}{fmt(total.cashflow)}
              </p>
            </div>
          </div>

          {/* Par structure */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {structures.map((s, i) => (
              <StructureCashflowCard key={i} data={s} />
            ))}
          </div>

          {/* Historique mensuel global */}
          {monthly.length > 0 && (
            <div className="pt-2">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                Historique mensuel
              </p>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {monthly.map((m, i) => (
                  <div key={i} className="flex-1 min-w-[80px] p-3 bg-white border border-slate-200 rounded-xl text-center">
                    <p className="text-xs font-semibold text-slate-600 mb-2">{m.label}</p>
                    <p className="text-xs text-emerald-600 font-medium">{fmt(m.loyers)}</p>
                    <p className="text-xs text-red-400">-{fmt(m.depenses)}</p>
                    <div className="mt-1.5 pt-1.5 border-t border-slate-100">
                      <p className={`text-xs font-bold ${m.cashflow >= 0 ? "text-emerald-600" : "text-red-500"}`}>
                        {m.cashflow >= 0 ? "+" : ""}{fmt(m.cashflow)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Rapport mensuel par associé */}
      <MonthlyAssociesTable associes={associes} monthly={monthly} />

      {/* Répartition par associé */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
            <Users className="w-5 h-5 text-slate-700" />
            Répartition par associé
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-slate-400">
            Cashflow net calculé selon les parts de chaque associé · Cliquez pour voir le détail
          </p>
          {associes.map((a, i) => (
            <AssocieCard key={i} data={a} />
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
