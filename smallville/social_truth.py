"""Guardrail épistémique : aucune croyance ne change de propriétaire sans être transmise.

Le contrôle lexical conservateur sert uniquement en l'absence de Jev.
Les énoncés produits par le LLM ne sont pas considérés comme des preuves de vérité.
"""
import re
import unicodedata

_STOP = set('''alors ainsi autre autres avant avoir beaucoup bien bonne celui celle ceux chez comme comment dans depuis dire elle elles encore entre etre faire fait faut gens grande grands ici jour leur leurs mais meme moi mon notre nous parce pendant personne personnes peux pour pourquoi quand quelque quelques quoi sans sont toute toutes tous tout tres une vous votre avec voici voila avait avoir vient etre enfin selon savoir village commune habitants habitant hier demain jour jours village loi lois meurtre interdit impossible charte avenir'''.split())


def _tokens(text):
    simple = unicodedata.normalize('NFKD', str(text or '').lower())
    simple = ''.join(c for c in simple if not unicodedata.combining(c))
    return {w for w in re.findall(r'[a-z]{4,}', simple) if w not in _STOP}


def explicitly_shared(utterance, proposition):
    """Preuve minimale de mention partagée, sans inférer de synonymes ou des vérités."""
    text, claim = _tokens(utterance), _tokens(proposition)
    if not text or not claim:
        return False
    overlap = text & claim
    # Des noms ou thèmes isolés ne suffisent pas à transférer une proposition.
    return len(overlap) >= 2 and (len(overlap)/len(claim) >= .22 or len(overlap) >= 3)
