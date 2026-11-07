"""Tests du diagnostic Jev : aucun appel réseau."""
import ssl
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smallville.jev import Jev,secure_tls_context
from smallville.settings import DEFAULT
from smallville.store import Store

class JevDiagnosticCase(TestCase):
    def test_tls_verifies_certificate(self):
        ctx=secure_tls_context()
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode,ssl.CERT_REQUIRED)

    def test_http_error_is_not_success_and_is_budgeted(self):
        import urllib.error
        with tempfile.TemporaryDirectory() as d:
            st=Store(Path(d)/'test.sqlite3')
            cfg=dict(DEFAULT,jev_enabled=True,jev_min_interval_seconds=1)
            client=Jev(st,cfg);client.key='FAKE'
            def fail(request,timeout=None):
                raise urllib.error.HTTPError(request.full_url,401,'bad key',None,None)
            client.opener.open=fail
            answers,reason=client._request(480,{'x':'a'},
                {'x':{'type':'noul','instructions':'Is x equal to a?'}})
            self.assertIsNone(answers)
            self.assertIn('HTTP 401',reason)
            self.assertEqual(st.budget(cfg)['calls'],1)
            self.assertNotIn('FAKE',reason)
