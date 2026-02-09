import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Calendar,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Users,
  TrendingUp,
  TrendingDown,
  Phone,
  MessageSquare
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MONTHS = [
  { value: 1, label: "Janvier" },
  { value: 2, label: "Février" },
  { value: 3, label: "Mars" },
  { value: 4, label: "Avril" },
  { value: 5, label: "Mai" },
  { value: 6, label: "Juin" },
  { value: 7, label: "Juillet" },
  { value: 8, label: "Août" },
  { value: 9, label: "Septembre" },
  { value: 10, label: "Octobre" },
  { value: 11, label: "Novembre" },
  { value: 12, label: "Décembre" },
];

export default function MonthlyReport() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [availableMonths, setAvailableMonths] = useState([]);

  const fetchAvailableMonths = async () => {
    try {
      const response = await axios.get(`${API}/payments/available-months`);
      setAvailableMonths(response.data.months);
    } catch (error) {
      console.error("Error fetching months:", error);
    }
  };

  const fetchMonthlyStatus = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/payments/monthly-status`, {
        params: { month: selectedMonth, year: selectedYear }
      });
      setData(response.data);
    } catch (error) {
      toast.error("Erreur lors du chargement des données");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAvailableMonths();
  }, []);

  useEffect(() => {
    fetchMonthlyStatus();
  }, [selectedMonth, selectedYear]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR"
    }).format(amount);
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short"
    });
  };

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 2 + i);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in" data-testid="monthly-report-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
            Rapport Mensuel
          </h1>
          <p className="text-slate-500 mt-1">
            Suivi des paiements par mois (du 28 au 28)
          </p>
        </div>
        <div className="flex gap-3">
          <Select value={selectedMonth.toString()} onValueChange={(v) => setSelectedMonth(parseInt(v))}>
            <SelectTrigger className="w-[140px]" data-testid="select-month">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MONTHS.map((m) => (
                <SelectItem key={m.value} value={m.value.toString()}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={selectedYear.toString()} onValueChange={(v) => setSelectedYear(parseInt(v))}>
            <SelectTrigger className="w-[100px]" data-testid="select-year">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {years.map((y) => (
                <SelectItem key={y} value={y.toString()}>
                  {y}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={fetchMonthlyStatus} data-testid="refresh-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {data && (
        <>
          {/* Period Info */}
          <div className="text-sm text-slate-500 flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Période: {formatDate(data.date_range?.start)} → {formatDate(data.date_range?.end)}
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="border-slate-200">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Total locataires</p>
                    <p className="text-3xl font-bold text-slate-900 mt-1" style={{ fontFamily: "Manrope" }}>
                      {data.summary?.total_tenants || 0}
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                    <Users className="w-6 h-6 text-slate-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-emerald-200 bg-emerald-50">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-emerald-700">Ont payé</p>
                    <p className="text-3xl font-bold text-emerald-900 mt-1" style={{ fontFamily: "Manrope" }}>
                      {data.summary?.paid_count || 0}
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-emerald-200 flex items-center justify-center">
                    <CheckCircle2 className="w-6 h-6 text-emerald-700" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-orange-200 bg-orange-50">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-orange-700">En attente</p>
                    <p className="text-3xl font-bold text-orange-600 mt-1" style={{ fontFamily: "Manrope" }}>
                      {data.summary?.unpaid_count || 0}
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-orange-200 flex items-center justify-center">
                    <AlertCircle className="w-6 h-6 text-orange-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Reste à percevoir</p>
                    <p className="text-2xl font-bold text-slate-900 mt-1" style={{ fontFamily: "Manrope" }}>
                      {formatCurrency(data.summary?.remaining || 0)}
                    </p>
                  </div>
                  <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
                    <TrendingDown className="w-6 h-6 text-slate-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Progress Bar */}
          <Card className="border-slate-200">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700">Progression des encaissements</span>
                <span className="text-sm font-bold text-emerald-700">
                  {data.summary?.total_expected > 0 
                    ? Math.round((data.summary.total_paid / data.summary.total_expected) * 100) 
                    : 0}%
                </span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-4">
                <div 
                  className="bg-emerald-600 h-4 rounded-full transition-all duration-500"
                  style={{ 
                    width: `${data.summary?.total_expected > 0 
                      ? Math.min(100, (data.summary.total_paid / data.summary.total_expected) * 100) 
                      : 0}%` 
                  }}
                />
              </div>
              <div className="flex justify-between mt-2 text-sm text-slate-500">
                <span>Collecté: {formatCurrency(data.summary?.total_paid || 0)}</span>
                <span>Attendu: {formatCurrency(data.summary?.total_expected || 0)}</span>
              </div>
            </CardContent>
          </Card>

          {/* Unpaid Tenants - Highlighted */}
          {data.unpaid_tenants?.length > 0 && (
            <Card className="border-orange-300 bg-orange-50" data-testid="unpaid-section">
              <CardHeader>
                <CardTitle className="text-orange-800 flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
                  <AlertCircle className="w-5 h-5" />
                  Locataires en attente de paiement ({data.unpaid_tenants.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow className="bg-orange-100">
                      <TableHead>Locataire</TableHead>
                      <TableHead>Adresse</TableHead>
                      <TableHead className="text-right">Loyer</TableHead>
                      <TableHead>Contact</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.unpaid_tenants.map((tenant) => (
                      <TableRow key={tenant.id} className="bg-white" data-testid={`unpaid-tenant-${tenant.id}`}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-orange-200 flex items-center justify-center">
                              <span className="text-orange-700 font-semibold text-sm">
                                {tenant.name?.charAt(0).toUpperCase()}
                              </span>
                            </div>
                            <span className="font-medium text-slate-900">{tenant.name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-slate-600 max-w-xs truncate">
                          {tenant.property_address}
                        </TableCell>
                        <TableCell className="text-right font-bold text-orange-700">
                          {formatCurrency(tenant.rent_amount)}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            {tenant.phone && (
                              <a 
                                href={`tel:${tenant.phone}`}
                                className="p-2 rounded-full bg-slate-100 hover:bg-slate-200 transition-colors"
                                title="Appeler"
                              >
                                <Phone className="w-4 h-4 text-slate-600" />
                              </a>
                            )}
                            {tenant.phone && (
                              <a 
                                href={`https://wa.me/${tenant.phone.replace(/[^0-9]/g, '')}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="p-2 rounded-full bg-emerald-100 hover:bg-emerald-200 transition-colors"
                                title="WhatsApp"
                              >
                                <MessageSquare className="w-4 h-4 text-emerald-600" />
                              </a>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* Paid Tenants */}
          {data.paid_tenants?.length > 0 && (
            <Card className="border-slate-200" data-testid="paid-section">
              <CardHeader>
                <CardTitle className="text-emerald-800 flex items-center gap-2" style={{ fontFamily: "Manrope" }}>
                  <CheckCircle2 className="w-5 h-5" />
                  Locataires ayant payé ({data.paid_tenants.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Locataire</TableHead>
                      <TableHead>Adresse</TableHead>
                      <TableHead className="text-right">Montant payé</TableHead>
                      <TableHead>Date paiement</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.paid_tenants.map((tenant) => (
                      <TableRow key={tenant.id} data-testid={`paid-tenant-${tenant.id}`}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center">
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            </div>
                            <span className="font-medium text-slate-900">{tenant.name}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-slate-600 max-w-xs truncate">
                          {tenant.property_address}
                        </TableCell>
                        <TableCell className="text-right font-bold text-emerald-700">
                          {formatCurrency(tenant.payment?.amount || tenant.rent_amount)}
                        </TableCell>
                        <TableCell className="text-slate-600">
                          {formatDate(tenant.payment?.date)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
