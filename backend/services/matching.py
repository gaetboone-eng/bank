import unicodedata
import re
from ..core.database import db


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text


def extract_name_words(text: str) -> list:
    text = normalize_text(text)
    stopwords = [
        'virement', 'sepa', 'recu', 'vir', 'inst', 'loyer', 'prlv', 'carte', 'cb',
        'mme', 'mlle', 'monsieur', 'madame', 'mr', 'dr', 'ei', 'sci', 'scr',
        'instantane', 'permanent', 'credit', 'debit', 'prelvt', 'bureau', 'msp',
        'cab', 'cabinet', 'fevrier', 'janvier', 'mars', 'avril', 'mai', 'juin',
        '2026', '2025', '202602', '202601', 'ics', 'fr', 'sca', 'ipr', 'loy',
        'med', 'maison', 'centre', 'mmc', 'seclin', 'docteur', 'juillet', 'aout',
        'septembre', 'octobre', 'novembre', 'decembre'
    ]
    words = text.split()
    return [w for w in words if len(w) > 2 and w not in stopwords]


def calculate_match_score(tenant_name: str, transaction_desc: str) -> int:
    tenant_normalized = normalize_text(tenant_name)
    tenant_parts = tenant_normalized.split()
    desc_words = extract_name_words(transaction_desc)
    desc_text = ' '.join(desc_words)

    score = 0
    for part in tenant_parts:
        if len(part) > 2:
            if part in desc_text:
                score += 10
            else:
                for word in desc_words:
                    if len(word) > 3 and len(part) > 3:
                        if word.startswith(part[:4]) or part.startswith(word[:4]):
                            score += 5
                            break
    return score


async def match_using_learned_rules(user_id: str, transaction_desc: str, amount: float):
    desc_keywords = extract_name_words(transaction_desc)
    desc_pattern = " ".join(desc_keywords[:5])

    rules = await db.matching_rules.find({"user_id": user_id}).to_list(1000)

    best_rule = None
    best_score = 0

    for rule in rules:
        rule_pattern = rule.get("pattern", "")
        rule_words = rule_pattern.split()

        score = 0
        for word in rule_words:
            if word in desc_pattern:
                score += 10
            elif any(word[:4] in dw or dw[:4] in word for dw in desc_keywords if len(dw) > 3 and len(word) > 3):
                score += 5

        rule_amount = rule.get("amount", 0)
        if rule_amount > 0:
            amount_diff = abs(amount - rule_amount) / rule_amount
            if amount_diff < 0.05:
                score += 15

        if score > best_score and score >= 15:
            best_score = score
            best_rule = rule

    return best_rule, best_score
