"""Tests indépendants de Jev et d'Apple, aucun accès Internet."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from smallville.social_truth import explicitly_shared
from smallville.jev import secure_tls_context
import ssl

class SocialTruthTests(unittest.TestCase):
    def test_cannot_invent_unspoken_rumor(self):
        rumor = 'Alice a entendu parler de guérisons incomprises : elle ne sait pas si la rumeur est vraie.'
        self.assertFalse(explicitly_shared('Le meurtre est interdit dans notre village.', rumor))
        self.assertFalse(explicitly_shared('Il est important de respecter les autres.', rumor))

    def test_gossip_must_be_voiced(self):
        rumor='Dorian craint que les récoltes ne suffisent pas à nourrir le village.'
        self.assertTrue(explicitly_shared('Dorian dit que les récoltes risquent de ne pas nourrir la communauté.',rumor))

    def test_tls_always_verifies(self):
        ctx=secure_tls_context()
        self.assertEqual(ctx.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

if __name__=='__main__':unittest.main()
