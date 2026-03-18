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
  ArrowRight,
  RefreshCw,
  Sparkles,
  Loader2
} from "lucide-react";
import { getDashboardStats, getTenants, getBanks, autoMatchTransactions, getPaymentStatsByStructure, manualSync, getCashflowHistory } from "@/lib/api";
import { toast } from "sonner";
import CashflowChart from "@/components/CashflowChart";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [banks, setBanks] = useState([]);
  const [structureStats, setStructureStats] = useState(null);
  const [cashflow, setCashflow] = useState({ history: [], structures: [], late_tenants: [] });
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, tenantsRes, banksRes, structureRes, cashflowRes] = await Promise.all([
        getDashboardStats(),
        getTenants(),
        getBanks(),
        getPaymentStatsByStructure(),
        getCashflowHistory()
      ]);
      setStats(statsRes.data);
      setTenants(tenantsRes.data);
      setBanks(banksRes.data);
      setStructureStats(structureRes.data);
      setCashflow(cashflowRes.data);
    } catch (error) {
      toast.error("Erreur lors du chargement des données");
    } finally {
      setLoading(false);
    }
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
      if (results.notion_sync.success) {
        message += `${results.notion_sync.count} locataires`;
      }
      if (results.bank_sync.success) {
        message += `, ${results.bank_sync.count} transactions`;
      }
      if (results.matching.success) {
        message += `, ${results.matching.count} matchés`;
      }
      
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR"
    }).format(amount);
  };

  const unpaidTenants = tenants.filter(t => t.payment_status !== "paid");
  const paidTenants = tenants.filter(t => t.payment_status === "paid");

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
            Tableau de bord
          </h1>
          <p className="text-sm sm:text-base text-slate-500 mt-1">
            Vue d'ensemble de vos locations
          </p>
        </div>
        <div className="flex gap-2 sm:gap-3">
          <Button 
            onClick={handleManualSync}
            disabled={syncing}
            variant="outline"
            className="gap-2 flex-1 sm:flex-none text-sm"
            data-testid="sync-btn"
            size="sm"
          >
            {syncing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="hidden sm:inline">Synchronisation...</span>
                <span className="sm:hidden">Sync...</span>
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                <span className="hidden sm:inline">Synchroniser</span>
                <span className="sm:hidden">Sync</span>
              </>
            )}
          </Button>
          <Button 
            onClick={handleAutoMatch}
            disabled={matching}
            className="bg-emerald-900 hover:bg-emerald-800 gap-2 flex-1 sm:flex-none text-sm"
            data-testid="match-btn"
            size="sm"
          >
            {matching ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="hidden sm:inline">Matching...</span>
                <span className="sm:hidden">Match...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span className="hidden sm:inline">Associer paiements</span>
                <span className="sm:hidden">Associer</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stats Grid - Bento Style */}
      <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
        {/* Total Tenants */}
        <Card className="border-slate-200" data-testid="stat-total-tenants">
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-slate-500">Locataires</p>
                <p className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.total_tenants || 0}
                </p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-slate-100 flex items-center justify-center">
                <Users className="w-5 h-5 sm:w-6 sm:h-6 text-slate-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Paid */}
        <Card className="border-slate-200" data-testid="stat-paid-tenants">
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-slate-500">Loyers payés</p>
                <p className="text-2xl sm:text-3xl font-bold text-emerald-900 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.paid_tenants || 0}
                </p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6 text-emerald-700" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Unpaid */}
        <Card className="border-slate-200" data-testid="stat-unpaid-tenants">
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-slate-500">Loyers impayés</p>
                <p className="text-2xl sm:text-3xl font-bold text-orange-500 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.unpaid_tenants || 0}
                </p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-orange-100 flex items-center justify-center">
                <AlertCircle className="w-5 h-5 sm:w-6 sm:h-6 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Banks */}
        <Card className="border-slate-200" data-testid="stat-banks">
          <CardContent className="p-4 sm:p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs sm:text-sm text-slate-500">Comptes bancaires</p>
                <p className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.banks_count || 0}
                </p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-slate-100 flex items-center justify-center">
                <Building2 className="w-5 h-5 sm:w-6 sm:h-6 text-slate-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Progress Bars Section */}
      {structureStats && (
        <div className="space-y-6">
          {/* Overall Progress */}
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
                <CheckCircle2 className="w-5 h-5 text-emerald-700" />
                Progression globale des paiements
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700">
                  {structureStats.overall.paid} / {structureStats.overall.total} locataires ont payé
                </span>
                <span className="text-lg font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>
                  {structureStats.overall.percentage}%
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-6">
                <div 
                  className="bg-emerald-600 h-6 rounded-full transition-all duration-500 flex items-center justify-end pr-3"
                  style={{ width: `${structureStats.overall.percentage}%` }}
                >
                  {structureStats.overall.percentage > 10 && (
                    <span className="text-white text-xs font-semibold">
                      {structureStats.overall.percentage}%
                    </span>
                  )}
                </div>
              </div>
              
              {/* Unpaid Tenants List */}
              {structureStats.overall.unpaid > 0 && (
                <div className="mt-4 p-3 sm:p-4 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex items-center gap-2 mb-2 sm:mb-3">
                    <AlertCircle className="w-4 h-4 text-orange-600" />
                    <h4 className="text-sm sm:text-base font-semibold text-orange-900">
                      Locataires en attente ({structureStats.overall.unpaid})
                    </h4>
                  </div>
                  <div className="flex flex-wrap gap-1.5 sm:gap-2">
                    {structureStats.overall.unpaid_names.map((name, idx) => (
                      <span 
                        key={idx}
                        className="px-2 sm:px-3 py-0.5 sm:py-1 bg-white text-orange-700 rounded-full text-xs sm:text-sm border border-orange-200"
                      >
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Progress by Structure */}
          {structureStats.by_structure.length > 1 && (
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
                  <Building2 className="w-5 h-5 text-slate-700" />
                  Progression par structure
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {structureStats.by_structure.map((structure, idx) => (
                  <div key={idx} className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-semibold text-slate-900">{structure.name}</h4>
                        <p className="text-sm text-slate-500">
                          {structure.paid} / {structure.total} locataires
                        </p>
                      </div>
                      <span className="text-lg font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>
                        {structure.percentage}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 rounded-full h-4">
                      <div 
                        className="bg-gradient-to-r from-emerald-500 to-emerald-600 h-4 rounded-full transition-all duration-500"
                        style={{ width: `${structure.percentage}%` }}
                      />
                    </div>
                    
                    {/* Unpaid tenants for this structure */}
                    {structure.unpaid > 0 && (
                      <div className="ml-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
                        <p className="text-xs text-slate-600 font-medium mb-2">
                          En attente ({structure.unpaid}) :
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {structure.unpaid_tenants.map((tenant, tidx) => (
                            <span 
                              key={tidx}
                              className="px-2 py-1 bg-white text-slate-700 rounded text-xs border border-slate-300"
                            >
                              {tenant.name} ({formatCurrency(tenant.rent_amount)})
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Cashflow Chart + Late Tenants */}
      <CashflowChart
        history={cashflow.history}
        structures={cashflow.structures}
        lateTenants={cashflow.late_tenants}
      />

      {/* Financial Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Expected vs Collected */}
        <Card className="border-slate-200" data-testid="financial-overview-card">
          <CardHeader>
            <CardTitle style={{ fontFamily: "Manrope" }}>Aperçu financier du mois</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-slate-600" />
                </div>
                <div>
                  <p className="text-sm text-slate-500">Loyers attendus</p>
                  <p className="text-xl font-bold text-slate-900" style={{ fontFamily: "Manrope" }}>
                    {formatCurrency(stats?.total_rent_expected || 0)}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-emerald-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-emerald-200 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-emerald-700" />
                </div>
                <div>
                  <p className="text-sm text-emerald-700">Loyers collectés</p>
                  <p className="text-xl font-bold text-emerald-900" style={{ fontFamily: "Manrope" }}>
                    {formatCurrency(stats?.total_rent_collected || 0)}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between p-4 bg-orange-50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-orange-200 flex items-center justify-center">
                  <TrendingDown className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <p className="text-sm text-orange-700">Reste à percevoir</p>
                  <p className="text-xl font-bold text-orange-600" style={{ fontFamily: "Manrope" }}>
                    {formatCurrency((stats?.total_rent_expected || 0) - (stats?.total_rent_collected || 0))}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Banks Overview */}
        <Card className="border-slate-200" data-testid="banks-overview-card">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle style={{ fontFamily: "Manrope" }}>Vos banques</CardTitle>
            <Link to="/banks">
              <Button variant="ghost" size="sm" data-testid="view-all-banks-btn">
                Voir tout <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-4">
            {banks.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Building2 className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                <p>Aucune banque configurée</p>
                <Link to="/banks">
                  <Button variant="outline" size="sm" className="mt-3" data-testid="add-first-bank-btn">
                    Ajouter une banque
                  </Button>
                </Link>
              </div>
            ) : (
              <>
                {banks.slice(0, 3).map((bank) => (
                  <div 
                    key={bank.id} 
                    className="flex items-center justify-between p-4 rounded-lg"
                    style={{ backgroundColor: `${bank.color}10` }}
                    data-testid={`bank-card-${bank.id}`}
                  >
                    <div className="flex items-center gap-3">
                      <div 
                        className="w-10 h-10 rounded-full flex items-center justify-center"
                        style={{ backgroundColor: bank.color }}
                      >
                        <Building2 className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{bank.name}</p>
                        {bank.iban && (
                          <p className="text-xs text-slate-500 font-mono">
                            {bank.iban.slice(-8)}
                          </p>
                        )}
                      </div>
                    </div>
                    <p className={`font-bold ${bank.balance >= 0 ? 'text-emerald-700' : 'text-red-600'}`} style={{ fontFamily: "Manrope" }}>
                      {formatCurrency(bank.balance)}
                    </p>
                  </div>
                ))}
                <div className="pt-2 border-t border-slate-100">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-500">Solde total</p>
                    <p className="text-xl font-bold text-slate-900" style={{ fontFamily: "Manrope" }}>
                      {formatCurrency(stats?.total_balance || 0)}
                    </p>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>


      {/* Recent Paid */}
      {paidTenants.length > 0 && (
        <Card className="border-slate-200" data-testid="paid-tenants-section">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle style={{ fontFamily: "Manrope" }}>
              Paiements reçus ce mois
            </CardTitle>
            <Link to="/tenants">
              <Button variant="ghost" size="sm" data-testid="view-all-tenants-btn">
                Voir tout <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {paidTenants.slice(0, 5).map((tenant) => (
                <div 
                  key={tenant.id} 
                  className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg"
                  data-testid={`paid-tenant-${tenant.id}`}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-200 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-emerald-700" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{tenant.name}</p>
                      <p className="text-sm text-slate-500">{tenant.property_address}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>
                      {formatCurrency(tenant.rent_amount)}
                    </p>
                    <span className="status-paid">Payé</span>
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
