import { useState, useEffect } from "react";
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
  Plus, 
  ArrowDownLeft, 
  ArrowUpRight, 
  RefreshCw,
  Filter,
  Loader2,
  Link as LinkIcon
} from "lucide-react";
import { getTransactions, createTransaction, getBanks, getTenants, matchTransaction } from "@/lib/api";
import { toast } from "sonner";

const CATEGORIES = [
  // Recettes
  { value: "loyer_encaisse", label: "Loyer encaissé", color: "#10b981", type: "income" },
  { value: "autre_recette", label: "Autre recette", color: "#34d399", type: "income" },
  // Charges
  { value: "eau_gaz_electricite", label: "Eau, gaz, électricité", color: "#3b82f6", type: "expense" },
  { value: "entretien_reparation", label: "Entretien et réparation", color: "#f59e0b", type: "expense" },
  { value: "travaux_amelioration", label: "Travaux d'amélioration", color: "#8b5cf6", type: "expense" },
  { value: "assurance", label: "Assurance", color: "#06b6d4", type: "expense" },
  { value: "internet_telephone", label: "Internet, téléphone", color: "#64748b", type: "expense" },
  { value: "abonnement_logiciel", label: "Abonnement logiciel", color: "#6366f1", type: "expense" },
  { value: "emprunt", label: "Emprunt", color: "#ef4444", type: "expense" },
  { value: "charges_copropriete", label: "Charges de copropriété", color: "#f97316", type: "expense" },
  { value: "autres_impots_taxes", label: "Autres impôts et taxes", color: "#dc2626", type: "expense" },
  { value: "frais_bancaires", label: "Frais bancaires", color: "#94a3b8", type: "expense" },
  { value: "virement_interne", label: "Virement interne", color: "#a8a29e", type: "neutral" },
  { value: "frais_divers", label: "Frais divers", color: "#78716c", type: "expense" },
  // Legacy
  { value: "rent", label: "Loyer encaissé", color: "#10b981", type: "income" },
  { value: "expense", label: "Dépense", color: "#78716c", type: "expense" },
  { value: "maintenance", label: "Entretien", color: "#f59e0b", type: "expense" },
  { value: "tax", label: "Impôts", color: "#dc2626", type: "expense" },
  { value: "deposit", label: "Dépôt", color: "#34d399", type: "income" },
  { value: "other", label: "Autre", color: "#78716c", type: "expense" },
];

export default function Transactions() {
  const [transactions, setTransactions] = useState([]);
  const [banks, setBanks] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [matchDialogOpen, setMatchDialogOpen] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [filterBank, setFilterBank] = useState("all");
  const [formData, setFormData] = useState({
    bank_id: "",
    amount: "",
    description: "",
    transaction_date: new Date().toISOString().split("T")[0],
    category: "rent",
    reference: ""
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [txRes, banksRes, tenantsRes] = await Promise.all([
        getTransactions(filterBank !== "all" ? filterBank : null),
        getBanks(),
        getTenants()
      ]);
      setTransactions(txRes.data);
      setBanks(banksRes.data);
      setTenants(tenantsRes.data);
    } catch (error) {
      toast.error("Erreur lors du chargement");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [filterBank]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormLoading(true);

    try {
      await createTransaction({
        ...formData,
        amount: parseFloat(formData.amount),
        transaction_date: new Date(formData.transaction_date).toISOString()
      });
      toast.success("Transaction ajoutée");
      setDialogOpen(false);
      setFormData({
        bank_id: "",
        amount: "",
        description: "",
        transaction_date: new Date().toISOString().split("T")[0],
        category: "rent",
        reference: ""
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de l'ajout");
    } finally {
      setFormLoading(false);
    }
  };

  const handleMatch = async (tenantId) => {
    if (!selectedTransaction) return;

    try {
      await matchTransaction(selectedTransaction.id, tenantId);
      toast.success("Transaction associée au locataire");
      setMatchDialogOpen(false);
      setSelectedTransaction(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de l'association");
    }
  };

  const openMatchDialog = (transaction) => {
    setSelectedTransaction(transaction);
    setMatchDialogOpen(true);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR"
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("fr-FR", {
      day: "numeric",
      month: "short",
      year: "numeric"
    });
  };

  const totalIncome = transactions.filter(t => t.amount > 0).reduce((sum, t) => sum + t.amount, 0);
  const totalExpense = transactions.filter(t => t.amount < 0).reduce((sum, t) => sum + t.amount, 0);

  return (
    <div className="space-y-8 animate-fade-in" data-testid="transactions-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
            Transactions
          </h1>
          <p className="text-slate-500 mt-1">
            Suivez vos flux bancaires et associez-les aux locataires
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-emerald-900 hover:bg-emerald-800" data-testid="add-transaction-btn">
              <Plus className="w-4 h-4 mr-2" />
              Ajouter une transaction
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle style={{ fontFamily: "Manrope" }}>Nouvelle transaction</DialogTitle>
              <DialogDescription>
                Enregistrez une nouvelle transaction bancaire
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="bank_id">Banque *</Label>
                <Select 
                  value={formData.bank_id} 
                  onValueChange={(value) => setFormData({ ...formData, bank_id: value })}
                >
                  <SelectTrigger data-testid="transaction-bank-select">
                    <SelectValue placeholder="Sélectionner une banque" />
                  </SelectTrigger>
                  <SelectContent>
                    {banks.map(bank => (
                      <SelectItem key={bank.id} value={bank.id}>{bank.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="amount">Montant (€) *</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    placeholder="Ex: 850 ou -150"
                    required
                    data-testid="transaction-amount-input"
                  />
                  <p className="text-xs text-slate-500">
                    Positif = entrée, Négatif = sortie
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Catégorie</Label>
                  <Select 
                    value={formData.category} 
                    onValueChange={(value) => setFormData({ ...formData, category: value })}
                  >
                    <SelectTrigger data-testid="transaction-category-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map(cat => (
                        <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description *</Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Ex: Loyer janvier M. Dupont"
                  required
                  data-testid="transaction-description-input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="transaction_date">Date *</Label>
                  <Input
                    id="transaction_date"
                    type="date"
                    value={formData.transaction_date}
                    onChange={(e) => setFormData({ ...formData, transaction_date: e.target.value })}
                    required
                    data-testid="transaction-date-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="reference">Référence</Label>
                  <Input
                    id="reference"
                    value={formData.reference}
                    onChange={(e) => setFormData({ ...formData, reference: e.target.value })}
                    placeholder="Ex: VIR-2024-001"
                    className="font-mono"
                    data-testid="transaction-reference-input"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                  Annuler
                </Button>
                <Button 
                  type="submit" 
                  className="bg-emerald-900 hover:bg-emerald-800"
                  disabled={formLoading || !formData.bank_id}
                  data-testid="submit-transaction-btn"
                >
                  {formLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Ajouter
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Match Dialog */}
      <Dialog open={matchDialogOpen} onOpenChange={setMatchDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle style={{ fontFamily: "Manrope" }}>Associer au locataire</DialogTitle>
            <DialogDescription>
              Sélectionnez le locataire correspondant à cette transaction
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 max-h-[300px] overflow-y-auto">
            {tenants.filter(t => t.payment_status !== "paid").map(tenant => (
              <button
                key={tenant.id}
                onClick={() => handleMatch(tenant.id)}
                className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors text-left"
                data-testid={`match-tenant-${tenant.id}`}
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center">
                    <span className="text-orange-700 font-semibold">
                      {tenant.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">{tenant.name}</p>
                    <p className="text-sm text-slate-500">{tenant.property_address}</p>
                  </div>
                </div>
                <p className="font-medium text-slate-700">
                  {formatCurrency(tenant.rent_amount)}
                </p>
              </button>
            ))}
            {tenants.filter(t => t.payment_status !== "paid").length === 0 && (
              <p className="text-center text-slate-500 py-4">
                Tous les locataires ont payé ce mois
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-slate-200">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
              <ArrowDownLeft className="w-6 h-6 text-emerald-700" />
            </div>
            <div>
              <p className="text-2xl font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>
                {formatCurrency(totalIncome)}
              </p>
              <p className="text-sm text-slate-500">Entrées</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
              <ArrowUpRight className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600" style={{ fontFamily: "Manrope" }}>
                {formatCurrency(Math.abs(totalExpense))}
              </p>
              <p className="text-sm text-slate-500">Sorties</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
              <ArrowDownLeft className="w-6 h-6 text-slate-600" />
            </div>
            <div>
              <p className={`text-2xl font-bold ${totalIncome + totalExpense >= 0 ? 'text-emerald-700' : 'text-red-600'}`} style={{ fontFamily: "Manrope" }}>
                {formatCurrency(totalIncome + totalExpense)}
              </p>
              <p className="text-sm text-slate-500">Balance</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-4">
        <Filter className="w-4 h-4 text-slate-400" />
        <Select value={filterBank} onValueChange={setFilterBank}>
          <SelectTrigger className="w-[200px]" data-testid="filter-bank-select">
            <SelectValue placeholder="Filtrer par banque" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Toutes les banques</SelectItem>
            {banks.map(bank => (
              <SelectItem key={bank.id} value={bank.id}>{bank.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <Card className="border-slate-200">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
            </div>
          ) : transactions.length === 0 ? (
            <div className="empty-state py-16">
              <ArrowDownLeft className="empty-state-icon" />
              <p className="empty-state-title">Aucune transaction</p>
              <p className="empty-state-text">
                Ajoutez votre première transaction pour commencer
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Banque</TableHead>
                  <TableHead>Catégorie</TableHead>
                  <TableHead className="text-right">Montant</TableHead>
                  <TableHead>Locataire</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((tx) => {
                  const bank = banks.find(b => b.id === tx.bank_id);
                  const tenant = tx.matched_tenant_id 
                    ? tenants.find(t => t.id === tx.matched_tenant_id)
                    : null;
                  const category = CATEGORIES.find(c => c.value === tx.category);
                  
                  return (
                    <TableRow key={tx.id} data-testid={`transaction-row-${tx.id}`}>
                      <TableCell className="font-mono text-sm text-slate-500">
                        {formatDate(tx.transaction_date)}
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium text-slate-900">{tx.description}</p>
                          {tx.reference && (
                            <p className="text-xs text-slate-500 font-mono">{tx.reference}</p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: bank?.color || "#64748B" }}
                          />
                          <span className="text-slate-600">{bank?.name || "N/A"}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-slate-600">{category?.label || tx.category}</span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={`font-bold ${tx.amount >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
                          {tx.amount >= 0 ? "+" : ""}{formatCurrency(tx.amount)}
                        </span>
                      </TableCell>
                      <TableCell>
                        {tenant ? (
                          <span className="status-paid">{tenant.name}</span>
                        ) : tx.amount > 0 ? (
                          <span className="status-pending">Non associé</span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {!tx.matched_tenant_id && tx.amount > 0 && (
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => openMatchDialog(tx)}
                            data-testid={`match-transaction-${tx.id}`}
                          >
                            <LinkIcon className="w-4 h-4" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
