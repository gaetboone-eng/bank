---
name: appbank_architecture
description: Architecture complète du projet CGR Bank - gestionnaire de flux bancaires pour SCIs
type: project
---

# CGR Bank - Gestionnaire de flux bancaires pour SCIs

**Repo GitHub:** https://github.com/gaetboone-eng/bank

## Stack technique
- **Backend:** FastAPI (Python 3.11+), Motor (async MongoDB), APScheduler, PyJWT
- **Frontend:** React 18, Axios, Tailwind CSS, Shadcn UI, Recharts, Lucide React
- **Base de données:** MongoDB
- **Intégrations:** Enable Banking (Open Banking), Notion API, Telegram Bot API
- **Infra:** Kubernetes, Nginx reverse proxy, Supervisor

## Structure des dossiers
- `/backend/server.py` — Monolithe Python ~2500 lignes (à refactoriser)
- `/frontend/src/components/` — Composants React réutilisables
- `/frontend/src/pages/` — Pages principales
- `/frontend/src/lib/` — Utilitaires et appels API
- `/tests/` — Tests
- `PROJECT_SUMMARY.md`, `CLAUDE_HANDOFF.md`, `GITHUB_GUIDE.md` — Documentation architecture

## Collections MongoDB
| Collection | Rôle |
|-----------|------|
| users | Gestion des comptes avec support multi-organisations |
| tenants | Locataires avec flag `deactivated` |
| banks | Comptes bancaires connectés avec soldes |
| transactions | Transactions avec matching optionnel vers locataire |
| payments | Paiements de loyer par locataire et mois |
| connected_banks | Métadonnées Enable Banking |
| matching_rules | Patterns appris pour auto-matching |

## Endpoints API clés
- Auth: `POST /api/auth/register`, `/api/auth/login`
- Dashboard: `GET /api/dashboard/stats`, `GET /api/dashboard/monthly-history`
- Tenants: `GET /api/tenants`, `POST /api/tenants/sync-notion`
- Banks: `GET /api/banks`, `POST /api/banking/import-all`
- Transactions: `GET /api/transactions`, `POST /api/transactions/auto-match`
- Payments: `GET /api/payments`, `GET /api/payments/stats-by-structure`

## Algorithme de matching transactions → locataires
1. Normalisation du texte (suppression accents, minuscules)
2. Extraction de mots-clés (filtre stopwords: "virement", "loyer"...)
3. Score: exact match +10, partiel +5, pattern appris +15
4. Seuil minimum: 15 points pour auto-matching

## Design system
- **Typographie:** Manrope (titres), Plus Jakarta Sans (corps), JetBrains Mono (IBANs/IDs)
- **Couleur principale:** Deep Emerald `#064E3B` (boutons, statut payé)
- **Couleur alerte:** Alert Orange `#F97316` (non-payé, notifications)
- **Background:** Swiss White `#FFFFFF` / Off-White Slate `#F8FAFC`
- Layout: Bento Grid Mode B, texte aligné gauche, montants alignés droite

## Règles critiques de dev
- Ne jamais hardcoder URLs, ports ou credentials
- Toujours exclure `_id` MongoDB des réponses API
- Filtrer les locataires `deactivated: true` dans toutes les stats
- Utiliser `datetime.now(timezone.utc)` pour les timestamps
- Préfixer les IDs custom avec UUID, jamais des ObjectIds MongoDB bruts

## Priorités de développement (backlog)
- **P1:** Notifications Telegram pour loyers impayés
- **P2 (Urgent):** Refactoring backend (réduire le monolithe server.py) + UI matching manuel
- **P3:** Système de notifications email
- **P4:** Guide de déploiement self-hosting

## Problèmes connus
- Légère divergence entre `/api/dashboard/stats` et `/api/payments/stats-by-structure` (27 vs 28 locataires payés)
- 50 locataires de test sur 3 comptes utilisateurs

**Why:** Projet en production, fonctionnel. Contexte: gestion de SCIs immobilières.
**How to apply:** Toujours filtrer les `deactivated`, respecter le design system emerald/orange, ne pas hardcoder les configs.
