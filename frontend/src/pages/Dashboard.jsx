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
  Loader2
} from "lucide-react";
import { getDashboardStats, getTenants, getBanks, autoMatchTransactions } from "@/lib/api";
import { toast } from "sonner";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [matching, setMatching] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, tenantsRes, banksRes] = await Promise.all([
        getDashboardStats(),
        getTenants(),
        getBanks()
      ]);
      setStats(statsRes.data);
      setTenants(tenantsRes.data);
      setBanks(banksRes.data);
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
        fetchData(); // Refresh data
      } else {
        toast.info("Aucune nouvelle correspondance trouvée");
      }
    } catch (error) {
      toast.error("Erreur lors du matching automatique");
    } finally {
      setMatching(false);
    }
  };

  useEffect(() => {
    fetchData();
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
    <div className="space-y-8 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
            Tableau de bord
          </h1>
          <p className="text-slate-500 mt-1">
            Vue d'ensemble de vos locations
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            onClick={handleAutoMatch}
            disabled={matching}
            className="bg-emerald-900 hover:bg-emerald-800"
            data-testid="auto-match-btn"
          >
            {matching ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4 mr-2" />
            )}
            Matching auto
          </Button>
          <Button 
            variant="outline" 
            onClick={fetchData}
            data-testid="refresh-dashboard-btn"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Actualiser
        </Button>
      </div>

      {/* Stats Grid - Bento Style */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Tenants */}
        <Card className="border-slate-200" data-testid="stat-total-tenants">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Locataires</p>
                <p className="text-3xl font-bold text-slate-900 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.total_tenants || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                <Users className="w-6 h-6 text-slate-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Paid */}
        <Card className="border-slate-200" data-testid="stat-paid-tenants">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Loyers payés</p>
                <p className="text-3xl font-bold text-emerald-900 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.paid_tenants || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-emerald-700" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Unpaid */}
        <Card className="border-slate-200" data-testid="stat-unpaid-tenants">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Loyers impayés</p>
                <p className="text-3xl font-bold text-orange-500 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.unpaid_tenants || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Banks */}
        <Card className="border-slate-200" data-testid="stat-banks">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Comptes bancaires</p>
                <p className="text-3xl font-bold text-slate-900 mt-1" style={{ fontFamily: "Manrope" }}>
                  {stats?.banks_count || 0}
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                <Building2 className="w-6 h-6 text-slate-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

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

      {/* Unpaid Tenants Alert */}
      {unpaidTenants.length > 0 && (
        <Card className="border-orange-200 bg-orange-50" data-testid="unpaid-tenants-alert">
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-orange-600" />
              <CardTitle className="text-orange-800" style={{ fontFamily: "Manrope" }}>
                Loyers en attente ({unpaidTenants.length})
              </CardTitle>
            </div>
            <Link to="/tenants">
              <Button variant="outline" size="sm" className="border-orange-300 text-orange-700 hover:bg-orange-100" data-testid="view-unpaid-tenants-btn">
                Voir les détails <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {unpaidTenants.slice(0, 6).map((tenant) => (
                <Link 
                  key={tenant.id} 
                  to={`/tenants/${tenant.id}`}
                  className="flex items-center gap-3 p-3 bg-white rounded-lg border border-orange-200 hover:border-orange-300 transition-colors"
                  data-testid={`unpaid-tenant-${tenant.id}`}
                >
                  <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
                    <span className="text-orange-700 font-semibold">
                      {tenant.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 truncate">{tenant.name}</p>
                    <p className="text-sm text-orange-600 font-medium">
                      {formatCurrency(tenant.rent_amount)}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

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
