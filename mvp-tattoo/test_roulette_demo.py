"""Tests for the standalone roulette demo server."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import approleta


class RouletteDemoTests(unittest.TestCase):
    def setUp(self):
        approleta.app.config.update(TESTING=True)
        self.client = approleta.app.test_client()

    def test_serves_the_roulette_and_required_assets(self):
        page = self.client.get('/roleta.html')
        script = self.client.get('/script.js')
        roulette_script = self.client.get('/roleta.js')
        prizes = self.client.get('/api/prizes')
        for response in (page, script, roulette_script, prizes):
            self.addCleanup(response.close)

        self.assertEqual(page.status_code, 200)
        self.assertIn(b'id="spinButton"', page.data)
        self.assertEqual(script.status_code, 200)
        self.assertEqual(roulette_script.status_code, 200)
        self.assertEqual(prizes.status_code, 200)

    def test_public_preview_can_spin_repeatedly_without_issuing_coupons(self):
        for _ in range(3):
            response = self.client.post('/api/spins/preview', json={})
            self.addCleanup(response.close)
            data = response.get_json()

            self.assertEqual(response.status_code, 200)
            self.assertTrue(data['preview'])
            self.assertIn(data['result']['prizeName'], {p['name'] for p in approleta.DEMO_PRIZES})
            self.assertNotIn('coupon', data)


if __name__ == '__main__':
    unittest.main()
