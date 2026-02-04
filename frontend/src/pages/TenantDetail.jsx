import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
  ArrowLeft, 
  User, 
  MapPin, 
  Phone, 
  Mail, 
  Calendar,
  CreditCard,
  MessageSquare,
  Trash2,
  RefreshCw,
  Loader2,
  Send
} from "lucide-react";
import { getTenant, deleteTenant, getPayments, createPayment, getBanks, sendWhatsAppNotification } from "@/lib/api";
import { toast } from "sonner";

export default function TenantDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState(null);
  const [payments, setPayments] = useState([]);
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
  const [messageDialogOpen, setMessageDialogOpen] = useState(false);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [messageLoading, setMessageLoading] = useState(false);
  
  const [paymentForm, setPaymentForm] = useState({
    amount: "",
    payment_date: new Date().toISOString().split("T")[0],
    bank_id: "",
    month: new Date().toLocaleString("fr-FR", { month: "long" }),
    year: new Date().getFullYear()
  });

  const [message, setMessage] = useState("");

  const months = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
  ];

  const fetchData = async () => {
    setLoading(true);
    try {
      const [tenantRes, paymentsRes, banksRes] = await Promise.all([
        getTenant(id),
        getPayments(id),
        getBanks()
      ]);
      setTenant(tenantRes.data);
      setPayments(paymentsRes.data);
      setBanks(banksRes.data);
      setPaymentForm(prev => ({
        ...prev,
        amount: tenantRes.data.rent_amount.toString()
      }));
    } catch (error) {
      toast.error("Erreur lors du chargement");
      navigate("/tenants");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm("Êtes-vous sûr de vouloir supprimer ce locataire ?")) return;
    
    setDeleteLoading(true);
    try {
      await deleteTenant(id);
      toast.success("Locataire supprimé");
      navigate("/tenants");
    } catch (error) {
      toast.error("Erreur lors de la suppression");
    } finally {
      setDeleteLoading(false);
    }
  };

  const handlePaymentSubmit = async (e) => {
    e.preventDefault();
    setPaymentLoading(true);

    try {
      await createPayment({
        tenant_id: id,
        amount: parseFloat(paymentForm.amount),
        payment_date: new Date(paymentForm.payment_date).toISOString(),
        bank_id: paymentForm.bank_id,
        month: paymentForm.month,
        year: parseInt(paymentForm.year)
      });
      toast.success("Paiement enregistré");
      setPaymentDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de l'enregistrement");
    } finally {
      setPaymentLoading(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    setMessageLoading(true);
    try {
      await sendWhatsAppNotification(id, message);
      toast.success("Message WhatsApp envoyé");
      setMessageDialogOpen(false);
      setMessage("");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de l'envoi");
    } finally {
      setMessageLoading(false);
    }
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
      month: "long",
      year: "numeric"
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
      </div>
    );
  }

  if (!tenant) return null;

  return (
    <div className="space-y-8 animate-fade-in" data-testid="tenant-detail-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/tenants">
            <Button variant="ghost" size="icon" data-testid="back-to-tenants-btn">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center">
              <span className="text-2xl font-bold text-slate-600">
                {tenant.name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
                {tenant.name}
              </h1>
              <p className="text-slate-500">{tenant.property_address}</p>
            </div>
          </div>
        </div>
        <div className="flex gap-3">
          <Dialog open={messageDialogOpen} onOpenChange={setMessageDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                variant="outline" 
                disabled={!tenant.phone}
                data-testid="send-whatsapp-btn"
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                WhatsApp
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: "Manrope" }}>Envoyer un message WhatsApp</DialogTitle>
                <DialogDescription>
                  Envoyez un rappel de paiement à {tenant.name}
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleSendMessage} className="space-y-4">
                <div className="space-y-2">
                  <Label>Destinataire</Label>
                  <p className="text-sm text-slate-600">{tenant.phone}</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="message">Message</Label>
                  <Textarea
                    id="message"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder={`Bonjour ${tenant.name}, ceci est un rappel pour votre loyer du mois...`}
                    rows={4}
                    data-testid="whatsapp-message-input"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setMessageDialogOpen(false)}>
                    Annuler
                  </Button>
                  <Button 
                    type="submit" 
                    className="bg-emerald-900 hover:bg-emerald-800"
                    disabled={messageLoading || !message.trim()}
                    data-testid="send-message-btn"
                  >
                    {messageLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
                    Envoyer
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
          
          <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-emerald-900 hover:bg-emerald-800" data-testid="add-payment-btn">
                <CreditCard className="w-4 h-4 mr-2" />
                Enregistrer paiement
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle style={{ fontFamily: "Manrope" }}>Enregistrer un paiement</DialogTitle>
                <DialogDescription>
                  Enregistrez un paiement de loyer pour {tenant.name}
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handlePaymentSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="month">Mois</Label>
                    <Select 
                      value={paymentForm.month} 
                      onValueChange={(value) => setPaymentForm({ ...paymentForm, month: value })}
                    >
                      <SelectTrigger data-testid="payment-month-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {months.map(month => (
                          <SelectItem key={month} value={month}>{month}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="year">Année</Label>
                    <Input
                      id="year"
                      type="number"
                      value={paymentForm.year}
                      onChange={(e) => setPaymentForm({ ...paymentForm, year: e.target.value })}
                      data-testid="payment-year-input"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="amount">Montant (€)</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                    required
                    data-testid="payment-amount-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="payment_date">Date de paiement</Label>
                  <Input
                    id="payment_date"
                    type="date"
                    value={paymentForm.payment_date}
                    onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })}
                    required
                    data-testid="payment-date-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bank_id">Banque</Label>
                  <Select 
                    value={paymentForm.bank_id} 
                    onValueChange={(value) => setPaymentForm({ ...paymentForm, bank_id: value })}
                  >
                    <SelectTrigger data-testid="payment-bank-select">
                      <SelectValue placeholder="Sélectionner une banque" />
                    </SelectTrigger>
                    <SelectContent>
                      {banks.map(bank => (
                        <SelectItem key={bank.id} value={bank.id}>{bank.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setPaymentDialogOpen(false)}>
                    Annuler
                  </Button>
                  <Button 
                    type="submit" 
                    className="bg-emerald-900 hover:bg-emerald-800"
                    disabled={paymentLoading || !paymentForm.bank_id}
                    data-testid="submit-payment-btn"
                  >
                    {paymentLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                    Enregistrer
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tenant Info */}
        <Card className="border-slate-200 lg:col-span-1" data-testid="tenant-info-card">
          <CardHeader>
            <CardTitle style={{ fontFamily: "Manrope" }}>Informations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <User className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-sm text-slate-500">Nom</p>
                <p className="font-medium text-slate-900">{tenant.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-sm text-slate-500">Adresse du bien</p>
                <p className="font-medium text-slate-900">{tenant.property_address}</p>
              </div>
            </div>
            {tenant.email && (
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-slate-400" />
                <div>
                  <p className="text-sm text-slate-500">Email</p>
                  <p className="font-medium text-slate-900">{tenant.email}</p>
                </div>
              </div>
            )}
            {tenant.phone && (
              <div className="flex items-center gap-3">
                <Phone className="w-5 h-5 text-slate-400" />
                <div>
                  <p className="text-sm text-slate-500">Téléphone</p>
                  <p className="font-medium text-slate-900">{tenant.phone}</p>
                </div>
              </div>
            )}
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-sm text-slate-500">Échéance</p>
                <p className="font-medium text-slate-900">Le {tenant.due_day} de chaque mois</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <CreditCard className="w-5 h-5 text-slate-400" />
              <div>
                <p className="text-sm text-slate-500">Loyer mensuel</p>
                <p className="font-bold text-emerald-900 text-xl" style={{ fontFamily: "Manrope" }}>
                  {formatCurrency(tenant.rent_amount)}
                </p>
              </div>
            </div>
            <div className="pt-4 border-t border-slate-100">
              <p className="text-sm text-slate-500 mb-2">Statut du mois</p>
              <span className={tenant.payment_status === "paid" ? "status-paid" : "status-unpaid"}>
                {tenant.payment_status === "paid" ? "Payé" : "Impayé"}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Payment History */}
        <Card className="border-slate-200 lg:col-span-2" data-testid="payment-history-card">
          <CardHeader>
            <CardTitle style={{ fontFamily: "Manrope" }}>Historique des paiements</CardTitle>
          </CardHeader>
          <CardContent>
            {payments.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <CreditCard className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                <p>Aucun paiement enregistré</p>
              </div>
            ) : (
              <div className="space-y-3">
                {payments.map((payment) => {
                  const bank = banks.find(b => b.id === payment.bank_id);
                  return (
                    <div 
                      key={payment.id}
                      className="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
                      data-testid={`payment-${payment.id}`}
                    >
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                          <CreditCard className="w-5 h-5 text-emerald-700" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">
                            {payment.month} {payment.year}
                          </p>
                          <p className="text-sm text-slate-500">
                            {formatDate(payment.payment_date)} • {bank?.name || "Banque"}
                          </p>
                        </div>
                      </div>
                      <p className="font-bold text-emerald-700" style={{ fontFamily: "Manrope" }}>
                        {formatCurrency(payment.amount)}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Danger Zone */}
      <Card className="border-red-200 bg-red-50">
        <CardHeader>
          <CardTitle className="text-red-800" style={{ fontFamily: "Manrope" }}>Zone de danger</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-700 mb-4">
            La suppression d'un locataire est irréversible et supprimera également son historique de paiements.
          </p>
          <Button 
            variant="destructive" 
            onClick={handleDelete}
            disabled={deleteLoading}
            data-testid="delete-tenant-btn"
          >
            {deleteLoading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Trash2 className="w-4 h-4 mr-2" />
            )}
            Supprimer ce locataire
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
