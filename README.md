# 🏦 CGR Bank - Tenant Finance Manager

> Assistant bancaire intelligent pour la gestion automatisée des paiements de loyers

[![Made with Emergent](https://img.shields.io/badge/Made%20with-Emergent-00C853?style=flat-square)](https://emergentagent.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com)

## 📋 Description

CGR Bank est une application full-stack qui automatise la gestion des paiements de loyers en :
- 🏦 Se connectant à vos comptes bancaires via Open Banking (Enable Banking)
- 📝 Synchronisant automatiquement vos locataires depuis Notion
- 🤖 Associant intelligemment les transactions bancaires aux locataires
- 📊 Générant des rapports visuels et des statistiques en temps réel
- 🔔 Envoyant des notifications pour les loyers impayés (à venir)

## ✨ Fonctionnalités principales

### ✅ Actuellement disponibles

- **Authentification sécurisée** - JWT avec support multi-utilisateurs
- **Dashboard interactif** - Statistiques en temps réel, graphiques, barres de progression
- **Graphique historique** - Visualisation de l'évolution des paiements sur 6 mois
- **Synchronisation Notion** - Import automatique des données locataires
- **Open Banking** - Connexion et import automatique de tous vos comptes bancaires
- **Matching intelligent** - Association automatique transactions ↔ locataires avec apprentissage
- **Gestion des structures** - Suivi par propriété (Hem, Seclin, Armentières, etc.)
- **Locataires résiliés** - Exclusion automatique des statistiques
- **PWA** - Installation sur mobile et desktop
- **Synchronisation manuelle** - Bouton de sync on-demand

### 🚧 En développement

- **Notifications Telegram** - Alertes automatiques pour impayés
- **Matching manuel** - Interface pour associations manuelles
- **Notifications Email** - Alternative aux notifications Telegram
- **Rapports avancés** - Export PDF, analyses mensuelles

## 🚀 Démarrage rapide

### Prérequis

- Node.js 18+
- Python 3.11+
- MongoDB 6+
- Compte Enable Banking (pour Open Banking)
- Base Notion (pour sync locataires)

### Installation

1. **Cloner le repository**
```bash
git clone https://github.com/votre-username/cgr-bank.git
cd cgr-bank
```

2. **Configuration Backend**
```bash
cd backend
pip install -r requirements.txt

# Créer le fichier .env
cp .env.example .env
# Éditer .env avec vos clés API
```

3. **Configuration Frontend**
```bash
cd frontend
yarn install

# Créer le fichier .env
cp .env.example .env
# Éditer .env avec l'URL du backend
```

4. **Lancer l'application**

Backend :
```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

Frontend :
```bash
cd frontend
yarn start
```

L'application sera accessible sur `http://localhost:3000`

## 🏗️ Architecture

### Stack technique

**Backend**
- FastAPI (API REST)
- MongoDB avec Motor (async)
- APScheduler (tâches planifiées)
- PyJWT (authentification)
- Enable Banking SDK

**Frontend**
- React 18
- React Router
- Axios
- Tailwind CSS
- Shadcn UI
- Recharts

**Infrastructure**
- Kubernetes
- Nginx
- Supervisor

### Structure du projet

```
.
├── backend/
│   ├── server.py           # API principale
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── components/     # Composants réutilisables
│   │   ├── pages/          # Pages principales
│   │   └── lib/            # Utilitaires et API
│   ├── public/
│   └── package.json
├── PROJECT_SUMMARY.md      # Documentation détaillée
└── README.md               # Ce fichier
```

## 📊 Captures d'écran

### Dashboard principal
![Dashboard](https://via.placeholder.com/800x400?text=Dashboard+Screenshot)

### Graphique historique
![Graphique](https://via.placeholder.com/800x400?text=Graphique+Historique)

### Gestion des locataires
![Locataires](https://via.placeholder.com/800x400?text=Gestion+Locataires)

## 🔑 Configuration

### Variables d'environnement Backend

```bash
# MongoDB
MONGO_URL=mongodb://localhost:27017
DB_NAME=tenant_ledger

# JWT
SECRET_KEY=votre-secret-key

# Notion
NOTION_API_KEY=secret_xxxxx
NOTION_DATABASE_ID=xxxxx

# Enable Banking
ENABLE_BANKING_APP_ID=your-app-id
ENABLE_BANKING_PRIVATE_KEY=/path/to/key.pem

# Telegram (optionnel)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### Variables d'environnement Frontend

```bash
REACT_APP_BACKEND_URL=http://localhost:8001
```

## 📖 Documentation

Pour une documentation complète et détaillée, consultez :
- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - Guide complet pour développeurs
- [API Documentation](./docs/API.md) - Documentation des endpoints (à venir)

## 🧪 Tests

### Backend
```bash
cd backend
pytest
```

### Frontend
```bash
cd frontend
yarn test
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Committez vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Pushez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

## 📝 Roadmap

- [x] Authentification JWT
- [x] Dashboard avec statistiques
- [x] Synchronisation Notion
- [x] Intégration Open Banking
- [x] Matching automatique
- [x] Graphique historique
- [ ] Notifications Telegram
- [ ] Matching manuel (UI)
- [ ] Refactorisation backend
- [ ] Notifications Email
- [ ] Export PDF
- [ ] Tests automatisés
- [ ] Documentation API complète

## ⚠️ Notes importantes

### Limitations connues

1. **Backend monolithique** : Le fichier `server.py` fait 2500+ lignes et doit être refactorisé
2. **Incohérence mineure** : Légère différence de comptage entre deux endpoints de stats
3. **Tests** : Couverture de tests à améliorer

### Sécurité

- Les mots de passe sont hashés avec bcrypt
- Les tokens JWT ont une expiration de 24h
- Les clés API ne sont jamais exposées côté client
- Toutes les routes API nécessitent une authentification

## 📄 License

Ce projet est sous licence privée. Tous droits réservés CGR Bank.

## 👥 Auteurs

- **Gaetan Boone** - Propriétaire principal - gaet.boone@gmail.com
- Développé avec [Emergent AI](https://emergentagent.com)

## 🙏 Remerciements

- Enable Banking pour l'API Open Banking
- Notion pour l'API de synchronisation
- Shadcn UI pour les composants
- Emergent pour l'assistance au développement

## 📞 Support

Pour toute question ou problème :
- 📧 Email : gaet.boone@gmail.com
- 🌐 Demo : https://tenant-finance-mgr.preview.emergentagent.com

---

**Fait avec ❤️ et [Emergent AI](https://emergentagent.com)**
