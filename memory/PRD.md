# Tenant Ledger - PRD (Product Requirements Document)

## Problème Original
Application de gestion de flux bancaires pour propriétaire immobilier avec:
- Gestion de 3 banques différentes
- Suivi des paiements des locataires
- Base de données locataires sur Notion (synchronisation API)
- Notifications WhatsApp via Twilio
- Authentification JWT classique

## Architecture

### Backend (FastAPI)
- **Auth**: JWT avec bcrypt
- **Base de données**: MongoDB
- **Collections**: users, banks, tenants, transactions, payments, notifications, user_settings
- **Intégrations**: Notion API, Twilio WhatsApp

### Frontend (React)
- **UI Components**: Shadcn/UI
- **Styling**: Tailwind CSS avec thème Swiss (Emerald/Orange)
- **Fonts**: Manrope (headings), Plus Jakarta Sans (body)
- **State**: Context API pour auth

## User Personas
1. **Propriétaire immobilier** - Gère plusieurs biens locatifs, souhaite suivre les paiements en temps réel

## Core Requirements (Static)
1. Authentification sécurisée JWT
2. Gestion multi-banques (CRUD)
3. Gestion des locataires avec sync Notion
4. Suivi des transactions bancaires
5. Matching transactions/locataires
6. Tableau de bord avec statistiques
7. Notifications WhatsApp pour rappels

## Implémentation - Janvier 2026

### MVP Livré
- ✅ Auth (register/login/logout)
- ✅ Dashboard avec stats temps réel
- ✅ CRUD Banques avec solde
- ✅ CRUD Locataires avec statut paiement
- ✅ CRUD Transactions avec matching locataire
- ✅ Enregistrement paiements manuels
- ✅ Page paramètres Notion/Twilio
- ✅ Interface responsive (mobile/desktop)

### Endpoints API
- POST /api/auth/register
- POST /api/auth/login
- GET /api/auth/me
- GET/POST /api/banks
- PUT/DELETE /api/banks/{id}
- GET/POST /api/tenants
- PUT/DELETE /api/tenants/{id}
- POST /api/tenants/sync-notion
- GET/POST /api/transactions
- POST /api/transactions/{id}/match/{tenant_id}
- GET/POST /api/payments
- GET /api/dashboard/stats
- POST /api/notifications/whatsapp
- GET/PUT /api/settings

## Backlog Priorisé

### P0 (Bloquant)
- Aucun

### P1 (Important)
- Import CSV des transactions bancaires
- Rappels automatiques par date d'échéance
- Historique des notifications envoyées

### P2 (Nice to have)
- Graphiques de tendances (Recharts)
- Export PDF des rapports mensuels
- Multi-utilisateur (gestion d'équipe)
- Mode sombre

## Next Tasks
1. Configurer les clés Notion API et Twilio pour activer:
   - Synchronisation locataires depuis Notion
   - Envoi de rappels WhatsApp
2. Ajouter import CSV pour transactions bancaires
3. Implémenter les graphiques de tendances
