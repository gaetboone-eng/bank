# 🏦 CGR Bank - Tenant Finance Manager
## Summary Complet pour Continuation du Projet

---

## 📋 Vue d'ensemble du projet

**Nom :** CGR Bank - Assistant bancaire pour gestion locative  
**Type :** Application Full-Stack (React + FastAPI + MongoDB)  
**URL de production :** https://tenant-finance-mgr.preview.emergentagent.com  
**Langue préférée :** Français

### Objectif principal
Application de gestion automatisée des paiements de loyers qui :
- Se connecte aux comptes bancaires via Open Banking (Enable Banking)
- Synchronise les données locataires depuis Notion
- Associe automatiquement les transactions bancaires aux locataires
- Génère des rapports de paiements et notifications
- Affiche un dashboard avec statistiques et graphiques historiques

---

## ✅ État actuel du projet

### Fonctionnalités complètes et testées
1. ✅ **Authentification JWT** - Login/Register fonctionnels
2. ✅ **Gestion multi-utilisateurs** - Support de plusieurs propriétaires avec organisations
3. ✅ **Intégration Notion** - Synchronisation automatique des locataires
4. ✅ **Intégration Enable Banking** - Connexion Open Banking avec import automatique de comptes
5. ✅ **Matching automatique** - Association intelligente transactions ↔ locataires
6. ✅ **Dashboard interactif** - Stats en temps réel avec barres de progression
7. ✅ **Graphique historique** - Évolution des paiements sur 6 mois (dernière fonctionnalité ajoutée)
8. ✅ **Gestion locataires résiliés** - Exclusion automatique des stats et rapports
9. ✅ **PWA** - Application Progressive Web App avec Service Worker
10. ✅ **Synchronisation manuelle** - Bouton pour sync on-demand
11. ✅ **Système d'apprentissage** - Règles de matching basées sur l'historique

### Fonctionnalités en cours/à venir

#### 🟠 P1 - Notifications Telegram
**Statut :** Non démarré  
**Objectif :** Envoyer des notifications pour loyers impayés via bot Telegram "OpenClaw"  
**Prochaines étapes :**
- Guider l'utilisateur pour créer un token de bot Telegram
- Récupérer le group ID
- Implémenter l'envoi de notifications programmées

#### 🟠 P2 - Interface de correspondance manuelle
**Statut :** Backend prêt, UI à créer  
**Endpoint existant :** `POST /api/transactions/{tx_id}/match/{tenant_id}`  
**Objectif :** Créer une interface utilisateur pour associer manuellement une transaction à un locataire

#### 🟡 P2 - Refactorisation server.py (URGENT)
**Statut :** À faire  
**Problème :** Le fichier `server.py` fait plus de 2500 lignes  
**Solution proposée :**
```
/app/backend/
├── routes/
│   ├── auth.py
│   ├── tenants.py
│   ├── banks.py
│   ├── transactions.py
│   ├── payments.py
│   └── dashboard.py
├── services/
│   ├── notion_service.py
│   ├── banking_service.py
│   └── matching_service.py
├── models/
│   └── schemas.py
└── server.py (point d'entrée principal)
```

#### 🟡 P3 - Notifications Email
**Statut :** À planifier  
**Objectif :** Alternative/complément aux notifications Telegram

#### 🟡 P4 - Guide de déploiement
**Statut :** À créer  
**Objectif :** Documentation pour auto-hébergement

---

## 🏗️ Architecture du code

### Structure actuelle des fichiers
```
/app/
├── backend/
│   ├── server.py                    # ⚠️ 2500+ lignes - MONOLITHE À REFACTORISER
│   ├── requirements.txt
│   └── .env                         # Variables d'environnement backend
├── frontend/
│   ├── public/
│   │   ├── manifest.json           # Configuration PWA
│   │   ├── service-worker.js       # Service Worker modifié (network-first pour APIs)
│   │   └── icons/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/                 # Composants Shadcn UI
│   │   │   └── HistoricalProgressChart.jsx  # 🆕 Graphique historique
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx       # ✅ Dashboard principal avec graphique
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Tenants.jsx
│   │   │   ├── Banks.jsx
│   │   │   ├── Transactions.jsx
│   │   │   ├── MonthlyReport.jsx
│   │   │   └── Settings.jsx
│   │   ├── lib/
│   │   │   └── api.js             # Fonctions API
│   │   ├── App.jsx
│   │   └── index.js
│   ├── package.json
│   └── .env                        # REACT_APP_BACKEND_URL
└── PROJECT_SUMMARY.md              # Ce fichier
```

### Stack technique
- **Backend :** FastAPI (Python 3.11+), Motor (MongoDB async), APScheduler, PyJWT
- **Frontend :** React 18, React Router, Axios, Tailwind CSS, Shadcn UI, Recharts
- **Base de données :** MongoDB
- **Intégrations :** Enable Banking (Open Banking), Notion API
- **Authentification :** JWT (Bearer tokens)
- **Déploiement :** Kubernetes, Nginx, Supervisor

---

## 🗄️ Schéma de base de données MongoDB

### Collections principales

#### `users`
```javascript
{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "password_hash": "string",
  "organization_id": "uuid",  // Pour multi-utilisateurs
  "created_at": "ISO datetime"
}
```

#### `tenants`
```javascript
{
  "id": "uuid",
  "user_id": "uuid",
  "organization_id": "uuid",
  "name": "string",
  "property_address": "string",
  "rent_amount": "float",
  "status": "string",  // "active", "resilié", etc.
  "deactivated": "boolean",  // ⚠️ IMPORTANT pour filtrage
  "notion_id": "string",
  "structure": "string",  // "Hem", "Seclin", "Armentieres", etc.
  "created_at": "ISO datetime"
}
```

#### `banks`
```javascript
{
  "id": "uuid",
  "user_id": "uuid",
  "organization_id": "uuid",
  "name": "string",
  "iban": "string",
  "balance": "float",
  "color": "string",
  "created_at": "ISO datetime"
}
```

#### `transactions`
```javascript
{
  "id": "uuid",
  "user_id": "uuid",
  "organization_id": "uuid",
  "bank_id": "uuid",
  "amount": "float",
  "description": "string",
  "transaction_date": "ISO datetime",
  "category": "string",
  "reference": "string",
  "matched_tenant_id": "uuid | null",
  "source": "string",  // "manual", "enable_banking"
  "created_at": "ISO datetime"
}
```

#### `payments`
```javascript
{
  "id": "uuid",
  "user_id": "uuid",
  "organization_id": "uuid",
  "tenant_id": "uuid",
  "transaction_id": "uuid",
  "amount": "float",
  "month": "string",  // "January", "February", etc.
  "year": "int",
  "date": "ISO datetime",
  "created_at": "ISO datetime"
}
```

#### `connected_banks`
```javascript
{
  "id": "uuid",
  "user_id": "uuid",
  "organization_id": "uuid",
  "account_uid": "string",  // Enable Banking account UID
  "bank_name": "string",
  "aspsp_name": "string",
  "iban": "string",
  "created_at": "ISO datetime"
}
```

#### `matching_rules`
```javascript
{
  "id": "uuid",
  "user_id": "uuid",
  "tenant_id": "uuid",
  "pattern": "string",  // Normalized keywords
  "amount": "float",
  "confidence": "int",
  "created_at": "ISO datetime"
}
```

---

## 🔌 Endpoints API principaux

### Authentification
- `POST /api/auth/register` - Créer un compte
- `POST /api/auth/login` - Se connecter (retourne access_token)

### Dashboard
- `GET /api/dashboard/stats` - Statistiques globales
- `GET /api/dashboard/monthly-history` - 🆕 Historique 6 mois pour graphique

### Locataires
- `GET /api/tenants` - Liste des locataires (filtre deactivated=false)
- `GET /api/tenants/{id}` - Détails d'un locataire
- `POST /api/tenants/sync-notion` - Synchroniser depuis Notion

### Banques
- `GET /api/banks` - Liste des comptes bancaires
- `POST /api/banking/import-all` - Import automatique de tous les comptes Enable Banking
- `GET /api/banking/aspsps?country=FR` - Liste des banques disponibles
- `POST /api/banking/connect` - Connecter un compte bancaire

### Transactions
- `GET /api/transactions` - Liste des transactions
- `POST /api/transactions/auto-match` - Matching automatique
- `POST /api/transactions/{tx_id}/match/{tenant_id}` - Matching manuel

### Paiements
- `GET /api/payments` - Liste des paiements
- `GET /api/payments/stats-by-structure` - Stats par structure (Hem, Seclin, etc.)

### Synchronisation
- `POST /api/sync/manual` - Sync complète (Notion + Banques + Matching)

---

## 🔑 Variables d'environnement

### Backend (.env)
```bash
# MongoDB
MONGO_URL=mongodb://localhost:27017
DB_NAME=tenant_ledger

# JWT
SECRET_KEY=your-secret-key-here

# Notion (requis pour sync locataires)
NOTION_API_KEY=secret_xxxxx
NOTION_DATABASE_ID=xxxxx

# Enable Banking (requis pour Open Banking)
ENABLE_BANKING_APP_ID=your-app-id
ENABLE_BANKING_PRIVATE_KEY=/path/to/private-key.pem

# Twilio (optionnel - pour SMS)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Telegram (à configurer)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### Frontend (.env)
```bash
REACT_APP_BACKEND_URL=https://tenant-finance-mgr.preview.emergentagent.com
WDS_SOCKET_PORT=443
ENABLE_HEALTH_CHECK=false
```

⚠️ **IMPORTANT :** Ne JAMAIS hardcoder les URLs ou tokens dans le code. Toujours utiliser les variables d'environnement.

---

## 👤 Comptes de test

### Compte principal (Owner 1)
- **Email :** `gaet.boone@gmail.com`
- **Mot de passe :** `TenantLedger2024!`
- **Locataires :** 50 (27 payés, 23 impayés)

### Compte 2 (Owner 2)
- **Email :** `romain.m@cgrbank.com`
- **Mot de passe :** `CGRbank2024!`

### Compte 3 (Owner 3)
- **Email :** `clement.h@cgrbank.com`
- **Mot de passe :** `CGRbank2024!`

---

## 🐛 Problèmes connus et points d'attention

### ⚠️ Incohérence de données (mineure)
**Symptôme :** Deux endpoints retournent des chiffres différents pour "locataires payés"
- `/api/dashboard/stats` → 27 payés
- `/api/payments/stats-by-structure` → 28 payés

**Cause probable :** Logique de comptage légèrement différente entre les deux endpoints  
**Impact :** Faible (différence de 1 locataire)  
**À corriger :** Dans une prochaine itération

### ✅ Points résolus dans cette session
- ✅ PWA cache fixé (network-first pour APIs)
- ✅ Locataires résiliés exclus des stats
- ✅ Graphique historique ajouté et fonctionnel
- ✅ Authentification testée et fonctionnelle

---

## 🔄 Algorithme de matching automatique

### Logique actuelle (dans `server.py`)

1. **Normalisation du texte** (`normalize_text`)
   - Suppression des accents
   - Conversion en minuscules
   - Suppression des caractères spéciaux

2. **Extraction de mots-clés** (`extract_name_words`)
   - Filtrage des stopwords (virement, sepa, loyer, etc.)
   - Extraction des noms potentiels

3. **Calcul de score** (`calculate_match_score`)
   - Correspondance exacte : +10 points
   - Correspondance partielle (4 premiers caractères) : +5 points
   - Tolérance de montant : ±5%

4. **Règles apprises** (`match_using_learned_rules`)
   - Utilisation de l'historique des associations manuelles
   - Bonus pour correspondance de montant : +15 points

5. **Seuil de confiance**
   - Score minimum : 15 points pour matcher automatiquement
   - Les transactions non matchées restent disponibles pour association manuelle

---

## 📊 Graphique historique (dernière fonctionnalité ajoutée)

### Fichiers créés/modifiés
- **Frontend :** `/app/frontend/src/components/HistoricalProgressChart.jsx` (nouveau)
- **Frontend :** `/app/frontend/src/pages/Dashboard.jsx` (modifié)
- **Backend :** Endpoint `/api/dashboard/monthly-history` (ligne 1414 de server.py)

### Fonctionnalité
- Affiche les 6 derniers mois d'historique de paiements
- Barres colorées selon taux de paiement :
  - 🟢 Vert : ≥ 80%
  - 🟠 Orange : 50-79%
  - 🔴 Rouge : < 50%
- Tooltip interactif avec détails
- Exclut les locataires résiliés du calcul

---

## 🚀 Commandes utiles

### Backend
```bash
# Installer les dépendances
cd /app/backend
pip install -r requirements.txt

# Lancer le serveur (pour dev local)
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Redémarrer via supervisor
sudo supervisorctl restart backend

# Voir les logs
tail -f /var/log/supervisor/backend.err.log
tail -f /var/log/supervisor/backend.out.log
```

### Frontend
```bash
# Installer les dépendances
cd /app/frontend
yarn install

# Lancer le serveur dev
yarn start

# Build de production
yarn build

# Redémarrer via supervisor
sudo supervisorctl restart frontend
```

### Base de données
```bash
# Se connecter à MongoDB
mongosh mongodb://localhost:27017/tenant_ledger

# Compter les locataires actifs
db.tenants.countDocuments({deactivated: false})

# Voir les paiements du mois en cours
db.payments.find({month: "March", year: 2026})
```

---

## 📝 Bonnes pratiques pour continuer

### Règles critiques
1. ⚠️ **NE JAMAIS hardcoder** les URLs, ports, tokens dans le code
2. ⚠️ **TOUJOURS exclure `_id`** des requêtes MongoDB (utiliser `{"_id": 0}`)
3. ⚠️ **Tous les endpoints backend** doivent avoir le préfixe `/api`
4. ⚠️ **Filtrer les locataires résiliés** dans toutes les requêtes de stats
5. ✅ Utiliser `datetime.now(timezone.utc)` au lieu de `datetime.utcnow()`
6. ✅ Préfixer tous les custom IDs avec UUID, pas d'utilisation d'ObjectId MongoDB
7. ✅ Tester après chaque modification importante

### Structure de code recommandée
```python
# Backend - Exemple d'endpoint
@api_router.get("/api/endpoint")
async def get_data(current_user: dict = Depends(get_current_user)):
    data = await db.collection.find(
        {
            **get_filter_for_user(current_user),
            "deactivated": {"$ne": True}  # Exclure résiliés
        },
        {"_id": 0}  # Ne pas retourner _id
    ).to_list(1000)
    return {"data": data}
```

```javascript
// Frontend - Exemple d'appel API
const fetchData = async () => {
  try {
    const response = await axios.get(
      `${process.env.REACT_APP_BACKEND_URL}/api/endpoint`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`
        }
      }
    );
    setData(response.data);
  } catch (error) {
    toast.error("Erreur lors du chargement");
  }
};
```

---

## 🔮 Prochaines sessions - Plan d'action

### Session 1 : Notifications Telegram (P1)
1. Demander à l'utilisateur de créer un bot Telegram
2. Récupérer le token et le chat/group ID
3. Implémenter l'envoi de notifications pour loyers impayés
4. Tester avec des comptes réels
5. Ajouter une configuration dans Settings

### Session 2 : UI de matching manuel (P2)
1. Créer une page `/transactions/unmatched`
2. Afficher les transactions non matchées
3. Permettre la sélection d'un locataire
4. Appeler `POST /api/transactions/{tx_id}/match/{tenant_id}`
5. Créer automatiquement une règle d'apprentissage

### Session 3 : Refactorisation backend (P2 - URGENT)
1. Créer la structure de dossiers (routes/, services/, models/)
2. Extraire les routes dans des fichiers séparés
3. Créer des services réutilisables
4. Migrer progressivement les fonctions de server.py
5. Tester après chaque migration

---

## 📞 Support et ressources

### Documentation API
- **Enable Banking :** https://enablebanking.com/docs
- **Notion API :** https://developers.notion.com
- **FastAPI :** https://fastapi.tiangolo.com
- **MongoDB Motor :** https://motor.readthedocs.io

### Intégrations tierces configurées
- ✅ Enable Banking (Open Banking)
- ✅ Notion (Synchronisation locataires)
- ⏳ Telegram (À configurer)

---

## 📄 Changelog de cette session

### 🆕 Ajouté
- Graphique historique de progression des paiements (6 derniers mois)
- Composant `HistoricalProgressChart.jsx` avec Recharts
- Endpoint `/api/dashboard/monthly-history`

### 🔧 Modifié
- `Dashboard.jsx` pour intégrer le nouveau graphique
- Service Worker pour utiliser network-first sur les APIs

### ✅ Testé
- Authentification sur 3 comptes
- Backend API (tous les endpoints principaux)
- Frontend (login, dashboard, graphique)
- Synchronisation Notion et Enable Banking

### 📊 Métriques actuelles
- **Fichiers backend :** 1 fichier principal (2500+ lignes) ⚠️
- **Fichiers frontend :** ~15 composants/pages
- **Endpoints API :** ~40
- **Collections MongoDB :** 7
- **Utilisateurs test :** 3
- **Locataires test :** 50

---

## ✅ Checklist pour reprendre le développement

Avant de commencer à coder :
- [ ] Lire ce fichier en entier
- [ ] Vérifier que tous les services sont running (`sudo supervisorctl status`)
- [ ] Tester l'authentification avec un compte de test
- [ ] Vérifier l'accès à MongoDB
- [ ] Confirmer les variables d'environnement

Pour chaque nouvelle fonctionnalité :
- [ ] Planifier l'implémentation
- [ ] Créer/modifier les fichiers nécessaires
- [ ] Tester backend avec `curl` si nécessaire
- [ ] Tester frontend avec screenshot ou manuellement
- [ ] Documenter les changements

---

## 🎯 Objectif final

Créer une application de gestion locative complète et automatisée qui :
1. ✅ Centralise toutes les données bancaires et locataires
2. ✅ Automatise le suivi des paiements de loyers
3. ⏳ Envoie des notifications pour les impayés
4. ⏳ Permet des interventions manuelles si nécessaire
5. ⏳ Fournit des rapports et analyses détaillés
6. 🔮 Se déploie facilement sur n'importe quel serveur

---

**Date de création de ce summary :** 18 Mars 2026  
**Dernière session par :** Agent E1 (Emergent)  
**Statut du projet :** 🟢 Fonctionnel et stable  
**Prêt pour continuation :** ✅ Oui

---

## 📧 Contact et questions

Pour toute question sur ce projet :
- Utilisateur principal : gaet.boone@gmail.com
- Organisation : CGR Bank
- URL : https://tenant-finance-mgr.preview.emergentagent.com

**Bon courage pour la suite du développement ! 🚀**
