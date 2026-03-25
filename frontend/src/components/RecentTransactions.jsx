import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight, ArrowDownLeft, ArrowUpRight, ArrowLeftRight } from "lucide-react";

const formatCurrency = (amount) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(amount);

const formatDate = (dateStr) => {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
};

const shortenDesc = (desc, maxLen = 40) => {
  if (!desc) return "";
  return desc.length > maxLen ? desc.slice(0, maxLen) + "…" : desc;
};

export default function RecentTransactions({ transactions = [] }) {
  if (!transactions.length) return null;

  return (
    <Card className="border-0 shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base font-semibold text-slate-800" style={{ fontFamily: "Manrope" }}>
          Dernières transactions
        </CardTitle>
        <Link to="/transactions">
          <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-700 gap-1 text-xs">
            Voir tout <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </Link>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-slate-100">
          {transactions.map((tx, idx) => {
            const isIncome = tx.amount > 0;
            const isNeutral = tx.category === "virement_interne";

            return (
              <div key={tx.id || idx} className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50 transition-colors">
                {/* Icon */}
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ backgroundColor: `${tx.category_color}20` }}
                >
                  {isNeutral ? (
                    <ArrowLeftRight className="w-3.5 h-3.5" style={{ color: tx.category_color }} />
                  ) : isIncome ? (
                    <ArrowDownLeft className="w-3.5 h-3.5" style={{ color: tx.category_color }} />
                  ) : (
                    <ArrowUpRight className="w-3.5 h-3.5" style={{ color: tx.category_color }} />
                  )}
                </div>

                {/* Description + category */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">
                    {shortenDesc(tx.description)}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span
                      className="text-xs px-1.5 py-0.5 rounded-full font-medium"
                      style={{
                        backgroundColor: `${tx.category_color}18`,
                        color: tx.category_color
                      }}
                    >
                      {tx.category_label}
                    </span>
                    {tx.bank_name && (
                      <span className="text-xs text-slate-400">{tx.bank_name}</span>
                    )}
                  </div>
                </div>

                {/* Amount + date */}
                <div className="text-right flex-shrink-0">
                  <p
                    className="text-sm font-semibold"
                    style={{ color: isNeutral ? "#64748b" : isIncome ? "#10b981" : "#1e293b" }}
                  >
                    {isIncome && !isNeutral ? "+" : ""}{formatCurrency(tx.amount)}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">{formatDate(tx.transaction_date)}</p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
