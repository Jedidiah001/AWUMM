import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from economy.negotiation import NegotiationOffer
from models.free_agent import FreeAgent, FreeAgentSource, FreeAgentVisibility
from models.free_agent_pool import FreeAgentPool
from models.free_agent_moods import FreeAgentMood
from persistence.database import Database
from persistence.free_agent_db import create_free_agent_tables, save_free_agent
from persistence.universe_db import DatabaseUniverseState
from services.free_agent_signing_service import finalize_free_agent_signing


class FreeAgentSigningServiceTests(unittest.TestCase):
    def setUp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        tmp_dir = os.path.join(root, "test_tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        self.db_path = os.path.join(tmp_dir, f"fa_signing_{uuid.uuid4().hex}.db")
        self.database = Database(self.db_path)
        create_free_agent_tables(self.database)
        self.universe = DatabaseUniverseState(self.database)

    def tearDown(self):
        self.database.close()
        for suffix in ("", "-wal", "-shm"):
            path = self.db_path + suffix
            if os.path.exists(path):
                os.remove(path)

    def test_finalize_signing_creates_roster_contract_and_marks_free_agent_signed(self):
        free_agent = FreeAgent(
            free_agent_id="fa_test_001",
            wrestler_id="w_signed_001",
            wrestler_name="Test Signee",
            age=29,
            gender="Male",
            alignment="Face",
            role="Midcard",
            brawling=62,
            technical=66,
            speed=61,
            mic=58,
            psychology=64,
            stamina=70,
            years_experience=7,
            popularity=55,
            source=FreeAgentSource.RELEASED,
            visibility=FreeAgentVisibility.INDUSTRY_BUZZ,
            mood=FreeAgentMood.HUNGRY,
            market_value=12000,
            discovered=True,
        )
        save_free_agent(self.database, free_agent)

        pool = FreeAgentPool(self.database)
        offer = NegotiationOffer(salary_per_show=15000, contract_weeks=78)
        offer.signing_bonus = 25000

        result = finalize_free_agent_signing(
            free_agent_pool=pool,
            universe=self.universe,
            database=self.database,
            free_agent_id=free_agent.id,
            offer=offer,
        )

        self.assertTrue(result["success"])
        wrestler = self.universe.get_wrestler_by_id("w_signed_001")
        self.assertIsNotNone(wrestler)
        self.assertEqual(wrestler.contract.salary_per_show, 15000)
        self.assertEqual(wrestler.contract.weeks_remaining, 78)
        self.assertIsNone(pool.get_free_agent_by_id(free_agent.id))

        row = self.database.conn.execute(
            "SELECT is_signed FROM free_agents WHERE id = ?",
            (free_agent.id,),
        ).fetchone()
        self.assertEqual(row["is_signed"], 1)


if __name__ == "__main__":
    unittest.main()
