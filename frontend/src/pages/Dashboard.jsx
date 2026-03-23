/* @babel-ignore */
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Users,
  Building2,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Loader2,
  Euro
} from "lucide-react";
import { getDashboardStats, getTenants, getBanks, autoMatchTransactions, getPaymentStatsByStructure, manualSync, getCashflowHistory } from "@/lib/api";
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
import { toast } from "sonner";
import CashflowChart from "@/components/CashflowChart";
import AssociesCashflow from "@/components/AssociesCashflow";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [banks, setBanks] = useState([]);
  const [structureStats, setStructureStats] = useState(null);
  const [cashflow, setCashflow] = useState({ history: [], structures: [], late_tenants: [] });
  const [monthlyHistory, setMonthlyHistory] = useState([]);
  const [structureCashflow, setStructureCashflow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, tenantsRes, banksRes, structureRes, cashflowRes, historyRes] = await Promise.all([
        getDashboardStats(),
        getTenants(),
        getBanks(),
        getPaymentStatsByStructure(),
        getCashflowHistory(),
        fetch(`${BACKEND_URL}/api/dashboard/monthly-history`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
        }).then(r => r.json())
      ]);
      setStats(statsRes.data);
      setTenants(tenantsRes.data);
      setBanks(banksRes.data);
      setStructureStats(structureRes.data);
      setCashflow(cashflowRes.data);
      setMonthlyHistory(historyRes.history || []);
    } catch (error) {
      toast.error("Erreur lors du chargement des données");
    } finally {
      setLoading(false);
    }
  };

  const fetchStructureCashflow = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${BACKEND_URL}/api/dashboard/structure-cashflow`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      if (data && data.structures) setStructureCashflow(data);
    } catch(e) { console.warn("structure-cashflow error", e); }
  };

  const handleAutoMatch = async () => {
    setMatching(true);
    try {
      const response = await autoMatchTransactions();
      const { matches } = response.data;
      if (matches.length > 0) {
        toast.success(`${matches.length} paiement(s) associé(s) automatiquement !`);
        fetchData();
      } else {
        toast.info("Aucune nouvelle correspondance trouvée");
      }
    } catch (error) {
      toast.error("Erreur lors du matching automatique");
    } finally {
      setMatching(false);
    }
  };

  const handleManualSync = async () => {
    setSyncing(true);
    try {
      const response = await manualSync();
      const results = response.data.results;
      let message = "Synchronisation terminée : ";
      if (results.notion_sync.success) message += `${results.notion_sync.count} locataires`;
      if (results.bank_sync.success) message += `, ${results.bank_sync.count} transactions`;
      if (results.matching.success) message += `, ${results.matching.count} matchés`;
      toast.success(message);
      fetchData();
    } catch (error) {
      toast.error("Erreur lors de la synchronisation");
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    fetchData();
    fetchStructureCashflow();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const formatCurrency = (amount) =>
    new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(amount);

  const unpaidTenants = tenants.filter(t => t.payment_status !== "paid");

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8 animate-fade-in" data-testid="dashboard-page">

      {/* ── HEADER ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
            Tableau de bord
          </h1>
          <p className="text-sm sm:text-base text-slate-500 mt-1">Vue d'ensemble de vos locations</p>
        </div>
        <div className="flex gap-2 sm:gap-3">
          <Button onClick={handleManualSync} disabled={syncing} variant="outline" className="gap-2 flex-1 sm:flex-none text-sm" size="sm">
            {syncing ? <><Loader2 className="w-4 h-4 animate-spin" /><span className="hidden sm:inline">Synchronisation...</span><span className="sm:hidden">Sync...</span></> : <><RefreshCw className="w-4 h-4" /><span className="hidden sm:inline">Synchroniser</span><span className="sm:hidden">Sync</span></>}
          </Button>
          <Button onClick={handleAutoMatch} disabled={matching} className="bg-emerald-900 hover:bg-emerald-800 gap-2 flex-1 sm:flex-none text-sm" size="sm">
            {matching ? <><Loader2 className="w-4 h-4 animate-spin" /><span className="hidden sm:inline">Matching...</span><span className="sm:hidden">Match...</span></> : <><Sparkles className="w-4 h-4" /><span className="hidden sm:inline">Associer paiements</span><span className="sm:hidden">Associer</span></>}
          </Button>
        </div>
      </div>

      {/* ── 1. TOTAL LOCATAIRES ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <Card className="border-0 shadow-sm overflow-hidden">
          <div className="h-1 bg-slate-400" />
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Locataires</p>
                <p className="text-3xl sm:text-4xl font-bold text-slate-900 mt-1.5 leading-none" style={{ fontFamily: "Manrope" }}>{stats?.total_tenants || 0}</p>
              </div>
              <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center mt-0.5">
                <Users className="w-4 h-4 text-slate-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm overflow-hidden">
          <div className="h-1 bg-emerald-500" />
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Payés</p>
                <p className="text-3xl sm:text-4xl font-bold text-emerald-600 mt-1.5 leading-none" style={{ fontFamily: "Manrope" }}>{stats?.paid_tenants || 0}</p>
              </div>
              <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center mt-0.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm overflow-hidden">
          <div className="h-1 bg-orange-400" />
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Impayés</p>
                <p className="text-3xl sm:text-4xl font-bold text-orange-500 mt-1.5 leading-none" style={{ fontFamily: "Manrope" }}>{stats?.unpaid_tenants || 0}</p>
              </div>
              <div className="w-9 h-9 rounded-xl bg-orange-50 flex items-center justify-center mt-0.5">
                <AlertCircle className="w-4 h-4 text-orange-500" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-0 shadow-sm overflow-hidden">
          <div className="h-1 bg-emerald-600" />
          <CardContent className="p-4 sm:p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Collecté</p>
                <p className="text-xl sm:text-2xl font-bold text-emerald-700 mt-1.5 leading-none" style={{ fontFamily: "Manrope" }}>{formatCurrency(stats?.total_rent_collected || 0)}</p>
                <p className="text-xs text-slate-400 mt-1">/ {formatCurrency(stats?.total_rent_expected || 0)}</p>
              </div>
              <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center mt-0.5">
                <Euro className="w-4 h-4 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── 2. INFOS PAR STRUCTURE ── */}
      {structureStats && structureStats.by_structure.length > 0 && (
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
              <Building2 className="w-5 h-5 text-slate-700" />
              Paiements par structure
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {structureStats.by_structure.map((structure, idx) => (
              <div key={idx} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-semibold text-slate-900">{structure.name}</h4>
                    <p className="text-sm text-slate-500">{structure.paid} / {structure.total} locataires</p>
                  </div>
                  <span className="text-lg font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>{structure.percentage}%</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-4">
                  <div
                    className="bg-gradient-to-r from-emerald-500 to-emerald-600 h-4 rounded-full transition-all duration-500"
                    style={{ width: `${structure.percentage}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs pt-0.5">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                    <span className="text-slate-500">Collecté :</span>
                    <span className="font-semibold text-emerald-700">{formatCurrency(structure.paid_amount || 0)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-orange-400" />
                    <span className="text-slate-500">Restant :</span>
                    <span className="font-semibold text-orange-600">{formatCurrency((structure.expected_amount || 0) - (structure.paid_amount || 0))}</span>
                  </div>
                </div>
              </div>
            ))}

            {/* Global bar */}
            {structureStats.overall && (
              <div className="pt-4 border-t border-slate-100 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-slate-700">Total global</span>
                  <span className="text-lg font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>{structureStats.overall.percentage}%</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-6">
                  <div
                    className="bg-emerald-600 h-6 rounded-full transition-all duration-500 flex items-center justify-end pr-3"
                    style={{ width: `${structureStats.overall.percentage}%` }}
                  >
                    {structureStats.overall.percentage > 10 && (
                      <span className="text-white text-xs font-semibold">{structureStats.overall.percentage}%</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── 3. RENTABILITÉ ── */}
      <CashflowChart history={monthlyHistory} lateTenants={[]} />
      <AssociesCashflow data={structureCashflow} />

      {/* ── 4. LOCATAIRES IMPAYÉS ── */}
      {unpaidTenants.length > 0 && (
        <Card className="border-orange-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-800" style={{ fontFamily: "Manrope" }}>
              <AlertCircle className="w-5 h-5 text-orange-500" />
              Locataires n'ayant pas encore payé ({unpaidTenants.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {unpaidTenants.map((tenant) => (
                <div key={tenant.id} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-100">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-orange-200 flex items-center justify-center shrink-0">
                      <Users className="w-4 h-4 text-orange-700" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900 text-sm">{tenant.name}</p>
                      <p className="text-xs text-slate-500">{tenant.property_address || tenant.structure}</p>
                    </div>
                  </div>
                  <div className="text-right shrink-0 ml-2">
                    <p className="font-bold text-orange-600 text-sm" style={{ fontFamily: "Manrope" }}>{formatCurrency(tenant.rent_amount)}</p>
                    <span className="text-xs text-orange-500">En attente</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

    </div>
  );
}
