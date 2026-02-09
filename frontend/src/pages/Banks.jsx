import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
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
  Plus, 
  Building2, 
  Pencil, 
  Trash2, 
  RefreshCw,
  Loader2,
  Link as LinkIcon,
  Unlink,
  Download
} from "lucide-react";
import { getBanks, createBank, updateBank, deleteBank, getAvailableAspsps, connectBankAccount, getConnectedBanks, syncBankTransactions, disconnectBank } from "@/lib/api";
import { toast } from "sonner";

const COLORS = [
  { name: "Émeraude", value: "#064E3B" },
  { name: "Bleu", value: "#1E40AF" },
  { name: "Violet", value: "#6D28D9" },
  { name: "Rose", value: "#BE185D" },
  { name: "Orange", value: "#C2410C" },
  { name: "Gris", value: "#374151" },
];

export default function Banks() {
  const [searchParams] = useSearchParams();
  const [banks, setBanks] = useState([]);
  const [connectedBanks, setConnectedBanks] = useState([]);
  const [availableAspsps, setAvailableAspsps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [connectDialogOpen, setConnectDialogOpen] = useState(false);
  const [editingBank, setEditingBank] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [connectLoading, setConnectLoading] = useState(false);
  const [selectedAspsp, setSelectedAspsp] = useState("");
  const [syncingAccount, setSyncingAccount] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    iban: "",
    balance: "0",
    color: "#064E3B"
  });

  // Handle callback params
  useEffect(() => {
    const connected = searchParams.get("connected");
    const accounts = searchParams.get("accounts");
    const error = searchParams.get("error");
    
    if (connected === "true") {
      toast.success(`${accounts} compte(s) bancaire(s) connecté(s) !`);
      // Clear URL params
      window.history.replaceState({}, "", "/banks");
    } else if (error) {
      toast.error(`Erreur de connexion: ${error}`);
      window.history.replaceState({}, "", "/banks");
    }
  }, [searchParams]);

  const fetchBanks = async () => {
    setLoading(true);
    try {
      const [banksRes, connectedRes] = await Promise.all([
        getBanks(),
        getConnectedBanks()
      ]);
      setBanks(banksRes.data);
      setConnectedBanks(connectedRes.data);
    } catch (error) {
      toast.error("Erreur lors du chargement des banques");
    } finally {
      setLoading(false);
    }
  };

  const fetchAvailableAspsps = async () => {
    try {
      const response = await getAvailableAspsps("FR");
      setAvailableAspsps(response.data);
    } catch (error) {
      console.error("Error fetching ASPSPs:", error);
    }
  };

  useEffect(() => {
    fetchBanks();
    fetchAvailableAspsps();
  }, []);

  const openEditDialog = (bank) => {
    setEditingBank(bank);
    setFormData({
      name: bank.name,
      iban: bank.iban || "",
      balance: bank.balance.toString(),
      color: bank.color
    });
    setDialogOpen(true);
  };

  const openCreateDialog = () => {
    setEditingBank(null);
    setFormData({
      name: "",
      iban: "",
      balance: "0",
      color: "#064E3B"
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormLoading(true);

    try {
      const data = {
        name: formData.name,
        iban: formData.iban || null,
        balance: parseFloat(formData.balance),
        color: formData.color
      };

      if (editingBank) {
        await updateBank(editingBank.id, data);
        toast.success("Banque mise à jour");
      } else {
        await createBank(data);
        toast.success("Banque ajoutée");
      }
      
      setDialogOpen(false);
      fetchBanks();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de l'opération");
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (bankId) => {
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer cette banque ?")) return;

    try {
      await deleteBank(bankId);
      toast.success("Banque supprimée");
      fetchBanks();
    } catch (error) {
      toast.error("Erreur lors de la suppression");
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "EUR"
    }).format(amount);
  };

  const totalBalance = banks.reduce((sum, bank) => sum + bank.balance, 0);

  return (
    <div className="space-y-8 animate-fade-in" data-testid="banks-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
            Banques
          </h1>
          <p className="text-slate-500 mt-1">
            Gérez vos comptes bancaires
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button 
              className="bg-emerald-900 hover:bg-emerald-800" 
              onClick={openCreateDialog}
              data-testid="add-bank-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Ajouter une banque
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle style={{ fontFamily: "Manrope" }}>
                {editingBank ? "Modifier la banque" : "Nouvelle banque"}
              </DialogTitle>
              <DialogDescription>
                {editingBank 
                  ? "Modifiez les informations de votre compte bancaire"
                  : "Ajoutez un nouveau compte bancaire à votre portefeuille"
                }
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Nom de la banque *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ex: Crédit Agricole"
                  required
                  data-testid="bank-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="iban">IBAN</Label>
                <Input
                  id="iban"
                  value={formData.iban}
                  onChange={(e) => setFormData({ ...formData, iban: e.target.value })}
                  placeholder="FR76 XXXX XXXX XXXX"
                  className="font-mono"
                  data-testid="bank-iban-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="balance">Solde actuel (€)</Label>
                <Input
                  id="balance"
                  type="number"
                  step="0.01"
                  value={formData.balance}
                  onChange={(e) => setFormData({ ...formData, balance: e.target.value })}
                  data-testid="bank-balance-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Couleur</Label>
                <div className="flex gap-2 flex-wrap">
                  {COLORS.map((color) => (
                    <button
                      key={color.value}
                      type="button"
                      className={`w-8 h-8 rounded-full transition-transform ${
                        formData.color === color.value 
                          ? "ring-2 ring-offset-2 ring-slate-400 scale-110" 
                          : "hover:scale-105"
                      }`}
                      style={{ backgroundColor: color.value }}
                      onClick={() => setFormData({ ...formData, color: color.value })}
                      title={color.name}
                      data-testid={`bank-color-${color.name}`}
                    />
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setDialogOpen(false)}
                  data-testid="cancel-bank-btn"
                >
                  Annuler
                </Button>
                <Button 
                  type="submit" 
                  className="bg-emerald-900 hover:bg-emerald-800"
                  disabled={formLoading}
                  data-testid="submit-bank-btn"
                >
                  {formLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  {editingBank ? "Mettre à jour" : "Ajouter"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Total Balance */}
      <Card className="border-slate-200 bg-gradient-to-br from-slate-900 to-slate-800">
        <CardContent className="p-8">
          <div className="text-white">
            <p className="text-slate-400 text-sm">Solde total</p>
            <p 
              className="text-4xl font-bold mt-2" 
              style={{ fontFamily: "Manrope" }}
              data-testid="total-balance"
            >
              {formatCurrency(totalBalance)}
            </p>
            <p className="text-slate-400 text-sm mt-2">
              {banks.length} compte{banks.length > 1 ? "s" : ""} bancaire{banks.length > 1 ? "s" : ""}
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Banks Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
        </div>
      ) : banks.length === 0 ? (
        <Card className="border-slate-200">
          <CardContent className="py-16">
            <div className="empty-state">
              <Building2 className="empty-state-icon" />
              <p className="empty-state-title">Aucune banque configurée</p>
              <p className="empty-state-text">
                Ajoutez vos comptes bancaires pour commencer à suivre vos flux
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {banks.map((bank) => (
            <Card 
              key={bank.id} 
              className="border-slate-200 overflow-hidden"
              data-testid={`bank-card-${bank.id}`}
            >
              <div 
                className="h-2" 
                style={{ backgroundColor: bank.color }}
              />
              <CardContent className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-12 h-12 rounded-full flex items-center justify-center"
                      style={{ backgroundColor: `${bank.color}20` }}
                    >
                      <Building2 className="w-6 h-6" style={{ color: bank.color }} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-900">{bank.name}</h3>
                      {bank.iban && (
                        <p className="text-xs text-slate-500 font-mono">
                          •••• {bank.iban.slice(-4)}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button 
                      variant="ghost" 
                      size="icon"
                      onClick={() => openEditDialog(bank)}
                      data-testid={`edit-bank-${bank.id}`}
                    >
                      <Pencil className="w-4 h-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon"
                      onClick={() => handleDelete(bank.id)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50"
                      data-testid={`delete-bank-${bank.id}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
                <div className="pt-4 border-t border-slate-100">
                  <p className="text-sm text-slate-500">Solde</p>
                  <p 
                    className={`text-2xl font-bold ${bank.balance >= 0 ? 'text-emerald-700' : 'text-red-600'}`}
                    style={{ fontFamily: "Manrope" }}
                  >
                    {formatCurrency(bank.balance)}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
