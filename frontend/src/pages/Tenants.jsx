import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Plus, 
  RefreshCw, 
  Search, 
  Users,
  ExternalLink,
  Loader2
} from "lucide-react";
import { getTenants, createTenant, syncTenantsFromNotion } from "@/lib/api";
import { toast } from "sonner";

export default function Tenants() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formLoading, setFormLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    property_address: "",
    rent_amount: "",
    due_day: "1"
  });

  const fetchTenants = async () => {
    setLoading(true);
    try {
      const response = await getTenants();
      setTenants(response.data);
    } catch (error) {
      toast.error("Erreur lors du chargement des locataires");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenants();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await syncTenantsFromNotion();
      toast.success(response.data.message);
      fetchTenants();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de la synchronisation");
    } finally {
      setSyncing(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormLoading(true);

    try {
      await createTenant({
        ...formData,
        rent_amount: parseFloat(formData.rent_amount),
        due_day: parseInt(formData.due_day)
      });
      toast.success("Locataire ajouté avec succès");
      setDialogOpen(false);
      setFormData({
        name: "",
        email: "",
        phone: "",
        property_address: "",
        rent_amount: "",
        due_day: "1"
      });
      fetchTenants();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de l'ajout");
    } finally {
      setFormLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR"
    }).format(amount);
  };

  const filteredTenants = tenants.filter(tenant =>
    tenant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tenant.property_address.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const paidCount = tenants.filter(t => t.payment_status === "paid").length;
  const unpaidCount = tenants.filter(t => t.payment_status !== "paid").length;

  return (
    <div className="space-y-8 animate-fade-in" data-testid="tenants-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
            Locataires
          </h1>
          <p className="text-slate-500 mt-1">
            Gérez vos locataires et suivez leurs paiements
          </p>
        </div>
        <div className="flex gap-3">
          <Button 
            variant="outline" 
            onClick={handleSync}
            disabled={syncing}
            data-testid="sync-notion-btn"
          >
            {syncing ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Sync Notion
          </Button>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-emerald-900 hover:bg-emerald-800" data-testid="add-tenant-btn">
                <Plus className="w-4 h-4 mr-2" />
                Ajouter
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: "Manrope" }}>Nouveau locataire</DialogTitle>
                <DialogDescription>
                  Ajoutez un nouveau locataire à votre portefeuille
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Nom complet *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    data-testid="tenant-name-input"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      data-testid="tenant-email-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Téléphone</Label>
                    <Input
                      id="phone"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      placeholder="+33612345678"
                      data-testid="tenant-phone-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="property_address">Adresse du bien *</Label>
                  <Input
                    id="property_address"
                    value={formData.property_address}
                    onChange={(e) => setFormData({ ...formData, property_address: e.target.value })}
                    required
                    data-testid="tenant-address-input"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="rent_amount">Loyer mensuel (€) *</Label>
                    <Input
                      id="rent_amount"
                      type="number"
                      step="0.01"
                      value={formData.rent_amount}
                      onChange={(e) => setFormData({ ...formData, rent_amount: e.target.value })}
                      required
                      data-testid="tenant-rent-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="due_day">Jour d'échéance</Label>
                    <Input
                      id="due_day"
                      type="number"
                      min="1"
                      max="31"
                      value={formData.due_day}
                      onChange={(e) => setFormData({ ...formData, due_day: e.target.value })}
                      data-testid="tenant-due-day-input"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button 
                    type="button" 
                    variant="outline" 
                    onClick={() => setDialogOpen(false)}
                    data-testid="cancel-tenant-btn"
                  >
                    Annuler
                  </Button>
                  <Button 
                    type="submit" 
                    className="bg-emerald-900 hover:bg-emerald-800"
                    disabled={formLoading}
                    data-testid="submit-tenant-btn"
                  >
                    {formLoading ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : null}
                    Ajouter
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-slate-200">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
              <Users className="w-6 h-6 text-slate-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900" style={{ fontFamily: "Manrope" }}>
                {tenants.length}
              </p>
              <p className="text-sm text-slate-500">Total locataires</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
              <Users className="w-6 h-6 text-emerald-700" />
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>
                {paidCount}
              </p>
              <p className="text-sm text-slate-500">Loyers payés</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center">
              <Users className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-orange-500" style={{ fontFamily: "Manrope" }}>
                {unpaidCount}
              </p>
              <p className="text-sm text-slate-500">Loyers en attente</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <Input
          placeholder="Rechercher un locataire..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
          data-testid="search-tenants-input"
        />
      </div>

      {/* Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
            </div>
          ) : filteredTenants.length === 0 ? (
            <div className="empty-state py-16">
              <Users className="empty-state-icon" />
              <p className="empty-state-title">Aucun locataire</p>
              <p className="empty-state-text">
                Ajoutez votre premier locataire ou synchronisez depuis Notion
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Locataire</TableHead>
                  <TableHead>Adresse</TableHead>
                  <TableHead className="text-right">Loyer</TableHead>
                  <TableHead>Échéance</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTenants.map((tenant) => (
                  <TableRow key={tenant.id} data-testid={`tenant-row-${tenant.id}`}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center">
                          <span className="text-slate-600 font-semibold">
                            {tenant.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{tenant.name}</p>
                          {tenant.email && (
                            <p className="text-sm text-slate-500">{tenant.email}</p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-slate-600 max-w-xs truncate">
                      {tenant.property_address}
                    </TableCell>
                    <TableCell className="text-right font-medium">
                      {formatCurrency(tenant.rent_amount)}
                    </TableCell>
                    <TableCell className="text-slate-600">
                      Le {tenant.due_day} du mois
                    </TableCell>
                    <TableCell>
                      <span className={tenant.payment_status === "paid" ? "status-paid" : "status-unpaid"}>
                        {tenant.payment_status === "paid" ? "Payé" : "Impayé"}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Link to={`/tenants/${tenant.id}`}>
                        <Button variant="ghost" size="sm" data-testid={`view-tenant-${tenant.id}`}>
                          <ExternalLink className="w-4 h-4" />
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
