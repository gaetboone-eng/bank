"""
Service de catégorisation automatique des transactions - style Indy
"""

# Définition complète des catégories style Indy
CATEGORIES = {
    # Recettes
    "loyer_encaisse": {
        "label": "Loyer encaissé",
        "color": "#10b981",
        "icon": "Home",
        "type": "income",
        "keywords": ["loyer", "quittance", "virement locataire", "locat"]
    },
    "autre_recette": {
        "label": "Autre recette",
        "color": "#34d399",
        "icon": "TrendingUp",
        "type": "income",
        "keywords": ["remboursement", "indemnite", "regularisation"]
    },

    # Charges exploitation
    "eau_gaz_electricite": {
        "label": "Eau, gaz, électricité",
        "color": "#3b82f6",
        "icon": "Zap",
        "type": "expense",
        "keywords": ["enedis", "edf", "gaz", "eau", "suez", "veolia", "electricite", "energie", "saur", "lyonnaise des eaux", "grdf"]
    },
    "entretien_reparation": {
        "label": "Entretien et réparation",
        "color": "#f59e0b",
        "icon": "Wrench",
        "type": "expense",
        "keywords": ["entretien", "reparation", "plombier", "electricien", "serrurier", "chauffage", "chaudiere", "plomberie", "bricolage", "leroy merlin", "brico"]
    },
    "travaux_amelioration": {
        "label": "Travaux d'amélioration",
        "color": "#8b5cf6",
        "icon": "HardHat",
        "type": "expense",
        "keywords": ["travaux", "renovation", "amenagement", "batiment", "construction", "materiau", "cloison", "peinture", "carrelage"]
    },
    "assurance": {
        "label": "Assurance",
        "color": "#06b6d4",
        "icon": "Shield",
        "type": "expense",
        "keywords": ["assurance", "mma", "maaf", "axa", "allianz", "groupama", "macif", "matmut", "pacifica", "generali", "cabinet ass"]
    },
    "internet_telephone": {
        "label": "Internet, téléphone, frais postaux",
        "color": "#64748b",
        "icon": "Phone",
        "type": "expense",
        "keywords": ["orange", "sfr", "bouygues", "free", "la poste", "chronopost", "colissimo", "telephone", "telecom", "internet"]
    },
    "abonnement_logiciel": {
        "label": "Abonnement logiciel",
        "color": "#6366f1",
        "icon": "Monitor",
        "type": "expense",
        "keywords": ["abonnement", "adobe", "microsoft", "google", "apple", "netflix", "saas", "logiciel", "notion", "dropbox"]
    },
    "emprunt": {
        "label": "Emprunt",
        "color": "#ef4444",
        "icon": "CreditCard",
        "type": "expense",
        "keywords": ["pret", "credit", "emprunt", "echeance", "lcl", "bnp", "credit agricole", "banque populaire", "caisse epargne", "mensualite", "remboursement pret"]
    },
    "charges_copropriete": {
        "label": "Charges de copropriété",
        "color": "#f97316",
        "icon": "Building",
        "type": "expense",
        "keywords": ["syndic", "copropriete", "charges copro", "foncia", "nexity", "gestia", "immo"]
    },
    "autres_impots_taxes": {
        "label": "Autres impôts et taxes",
        "color": "#dc2626",
        "icon": "Receipt",
        "type": "expense",
        "keywords": ["taxe", "impot", "foncier", "cfe", "tva", "dgfip", "tresor public", "dgi", "finances publiques"]
    },
    "frais_bancaires": {
        "label": "Frais bancaires",
        "color": "#94a3b8",
        "icon": "Landmark",
        "type": "expense",
        "keywords": ["frais bancaires", "cotisation carte", "agios", "commission", "frais tenue", "interets"]
    },
    "virement_interne": {
        "label": "Virement interne",
        "color": "#a8a29e",
        "icon": "ArrowLeftRight",
        "type": "neutral",
        "keywords": ["virement", "sci ", "sas ", "sarl ", "entre comptes"]
    },
    "frais_divers": {
        "label": "Frais divers",
        "color": "#78716c",
        "icon": "MoreHorizontal",
        "type": "expense",
        "keywords": []
    },

    # Legacy compatibility
    "rent": {
        "label": "Loyer encaissé",
        "color": "#10b981",
        "icon": "Home",
        "type": "income",
        "keywords": []
    },
    "expense": {
        "label": "Dépense",
        "color": "#78716c",
        "icon": "MoreHorizontal",
        "type": "expense",
        "keywords": []
    },
    "maintenance": {
        "label": "Entretien",
        "color": "#f59e0b",
        "icon": "Wrench",
        "type": "expense",
        "keywords": []
    },
    "tax": {
        "label": "Impôts",
        "color": "#dc2626",
        "icon": "Receipt",
        "type": "expense",
        "keywords": []
    },
    "deposit": {
        "label": "Dépôt",
        "color": "#34d399",
        "icon": "TrendingUp",
        "type": "income",
        "keywords": []
    },
    "other": {
        "label": "Autre",
        "color": "#78716c",
        "icon": "MoreHorizontal",
        "type": "expense",
        "keywords": []
    }
}


def auto_categorize(description: str, amount: float) -> str:
    """
    Catégorise automatiquement une transaction selon sa description et son montant.
    Retourne la clé de catégorie.
    """
    if not description:
        return "loyer_encaisse" if amount > 0 else "frais_divers"

    desc_lower = description.lower()

    # Recettes → loyer encaissé par défaut si positif
    if amount > 0:
        # Vérifier si c'est bien un loyer ou autre recette
        for kw in CATEGORIES["loyer_encaisse"]["keywords"]:
            if kw in desc_lower:
                return "loyer_encaisse"
        return "loyer_encaisse"  # Tout crédit = loyer par défaut

    # Dépenses → chercher la catégorie la plus probable
    # Ordre de priorité (du plus spécifique au plus général)
    priority_order = [
        "emprunt",
        "eau_gaz_electricite",
        "assurance",
        "entretien_reparation",
        "travaux_amelioration",
        "internet_telephone",
        "abonnement_logiciel",
        "charges_copropriete",
        "autres_impots_taxes",
        "frais_bancaires",
        "virement_interne",
    ]

    for cat_key in priority_order:
        cat = CATEGORIES[cat_key]
        for kw in cat["keywords"]:
            if kw in desc_lower:
                return cat_key

    return "frais_divers"


def get_category_info(category_key: str) -> dict:
    """Retourne les informations d'une catégorie."""
    return CATEGORIES.get(category_key, CATEGORIES["frais_divers"])


def normalize_category(category_key: str) -> str:
    """Normalise les anciennes catégories vers les nouvelles."""
    mapping = {
        "rent": "loyer_encaisse",
        "deposit": "autre_recette",
        "maintenance": "entretien_reparation",
        "tax": "autres_impots_taxes",
        "other": "frais_divers",
        "expense": "frais_divers",
    }
    return mapping.get(category_key, category_key)


# Liste pour le frontend
CATEGORIES_LIST = [
    {"value": "loyer_encaisse", "label": "Loyer encaissé", "color": "#10b981", "type": "income"},
    {"value": "autre_recette", "label": "Autre recette", "color": "#34d399", "type": "income"},
    {"value": "eau_gaz_electricite", "label": "Eau, gaz, électricité", "color": "#3b82f6", "type": "expense"},
    {"value": "entretien_reparation", "label": "Entretien et réparation", "color": "#f59e0b", "type": "expense"},
    {"value": "travaux_amelioration", "label": "Travaux d'amélioration", "color": "#8b5cf6", "type": "expense"},
    {"value": "assurance", "label": "Assurance", "color": "#06b6d4", "type": "expense"},
    {"value": "internet_telephone", "label": "Internet, téléphone", "color": "#64748b", "type": "expense"},
    {"value": "abonnement_logiciel", "label": "Abonnement logiciel", "color": "#6366f1", "type": "expense"},
    {"value": "emprunt", "label": "Emprunt", "color": "#ef4444", "type": "expense"},
    {"value": "charges_copropriete", "label": "Charges de copropriété", "color": "#f97316", "type": "expense"},
    {"value": "autres_impots_taxes", "label": "Autres impôts et taxes", "color": "#dc2626", "type": "expense"},
    {"value": "frais_bancaires", "label": "Frais bancaires", "color": "#94a3b8", "type": "expense"},
    {"value": "virement_interne", "label": "Virement interne", "color": "#a8a29e", "type": "neutral"},
    {"value": "frais_divers", "label": "Frais divers", "color": "#78716c", "type": "expense"},
]
