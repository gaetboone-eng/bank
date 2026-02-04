import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { 
  Settings as SettingsIcon, 
  Database, 
  MessageSquare, 
  RefreshCw,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ExternalLink
} from "lucide-react";
import { getSettings, updateSettings, syncTenantsFromNotion } from "@/lib/api";
import { toast } from "sonner";

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [formData, setFormData] = useState({
    notion_api_key: "",
    notion_database_id: ""
  });

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const response = await getSettings();
      setSettings(response.data);
      setFormData({
        notion_api_key: response.data.notion_api_key || "",
        notion_database_id: response.data.notion_database_id || ""
      });
    } catch (error) {
      toast.error("Erreur lors du chargement des paramètres");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await updateSettings(formData);
      toast.success("Paramètres enregistrés");
      fetchSettings();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de l'enregistrement");
    } finally {
      setSaving(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await syncTenantsFromNotion();
      toast.success(response.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Erreur lors de la synchronisation");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-900" />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in max-w-3xl" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight" style={{ fontFamily: "Manrope" }}>
          Paramètres
        </h1>
        <p className="text-slate-500 mt-1">
          Configurez vos intégrations et préférences
        </p>
      </div>

      {/* Notion Integration */}
      <Card className="border-slate-200" data-testid="notion-settings-card">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
              <Database className="w-5 h-5 text-slate-600" />
            </div>
            <div>
              <CardTitle style={{ fontFamily: "Manrope" }}>Notion</CardTitle>
              <CardDescription>
                Synchronisez vos locataires depuis Notion
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="notion_api_key">Clé API Notion</Label>
              <Input
                id="notion_api_key"
                type="password"
                value={formData.notion_api_key}
                onChange={(e) => setFormData({ ...formData, notion_api_key: e.target.value })}
                placeholder="ntn_xxxxxxxxxxxxx"
                className="font-mono"
                data-testid="notion-api-key-input"
              />
              <p className="text-xs text-slate-500">
                Obtenez votre clé API sur{" "}
                <a 
                  href="https://www.notion.so/my-integrations" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-emerald-700 hover:underline"
                >
                  notion.so/my-integrations
                  <ExternalLink className="w-3 h-3 inline ml-1" />
                </a>
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="notion_database_id">ID de la base de données</Label>
              <Input
                id="notion_database_id"
                value={formData.notion_database_id}
                onChange={(e) => setFormData({ ...formData, notion_database_id: e.target.value })}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="font-mono"
                data-testid="notion-database-id-input"
              />
              <p className="text-xs text-slate-500">
                L'ID se trouve dans l'URL de votre base de données Notion
              </p>
            </div>
            <div className="flex gap-3 pt-4">
              <Button 
                type="submit" 
                className="bg-emerald-900 hover:bg-emerald-800"
                disabled={saving}
                data-testid="save-notion-settings-btn"
              >
                {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Enregistrer
              </Button>
              <Button 
                type="button"
                variant="outline"
                onClick={handleSync}
                disabled={syncing || !formData.notion_api_key || !formData.notion_database_id}
                data-testid="sync-notion-btn"
              >
                {syncing ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4 mr-2" />
                )}
                Synchroniser maintenant
              </Button>
            </div>
          </form>

          {/* Notion Schema Info */}
          <div className="mt-6 p-4 bg-slate-50 rounded-lg">
            <h4 className="font-medium text-slate-900 mb-2">Structure attendue de la base Notion</h4>
            <p className="text-sm text-slate-600 mb-3">
              Votre base de données Notion doit contenir les propriétés suivantes :
            </p>
            <ul className="text-sm text-slate-600 space-y-1">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <strong>Name</strong> (titre) - Nom du locataire
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <strong>Email</strong> (email) - Adresse email
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <strong>Phone</strong> (téléphone) - Numéro de téléphone
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <strong>Address</strong> (texte) - Adresse du bien
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <strong>Rent</strong> ou <strong>Rent Amount</strong> (nombre) - Montant du loyer
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-slate-400" />
                <strong>Due Day</strong> (nombre) - Jour d'échéance (optionnel)
              </li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Twilio Integration */}
      <Card className="border-slate-200" data-testid="twilio-settings-card">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
              <MessageSquare className="w-5 h-5 text-slate-600" />
            </div>
            <div>
              <CardTitle style={{ fontFamily: "Manrope" }}>Twilio WhatsApp</CardTitle>
              <CardDescription>
                Envoyez des rappels de paiement par WhatsApp
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-3 p-4 rounded-lg bg-slate-50">
            {settings?.twilio_configured ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <div>
                  <p className="font-medium text-emerald-800">Twilio configuré</p>
                  <p className="text-sm text-slate-600">
                    Les notifications WhatsApp sont actives
                  </p>
                </div>
              </>
            ) : (
              <>
                <AlertCircle className="w-5 h-5 text-orange-500" />
                <div>
                  <p className="font-medium text-orange-800">Twilio non configuré</p>
                  <p className="text-sm text-slate-600">
                    Configurez les variables d'environnement TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN et TWILIO_WHATSAPP_FROM sur le serveur
                  </p>
                </div>
              </>
            )}
          </div>
          <div className="mt-4">
            <a 
              href="https://www.twilio.com/console" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-sm text-emerald-700 hover:underline flex items-center gap-1"
            >
              Configurer Twilio
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </CardContent>
      </Card>

      {/* App Info */}
      <Card className="border-slate-200">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
              <SettingsIcon className="w-5 h-5 text-emerald-700" />
            </div>
            <div>
              <CardTitle style={{ fontFamily: "Manrope" }}>Tenant Ledger</CardTitle>
              <CardDescription>
                Assistant bancaire pour la gestion immobilière
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm text-slate-600">
            <p><strong>Version:</strong> 1.0.0</p>
            <p><strong>Fonctionnalités:</strong></p>
            <ul className="list-disc list-inside pl-2 space-y-1">
              <li>Gestion de plusieurs comptes bancaires</li>
              <li>Suivi des locataires et paiements</li>
              <li>Synchronisation avec Notion</li>
              <li>Notifications WhatsApp via Twilio</li>
              <li>Matching automatique transactions/locataires</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
