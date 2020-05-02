import unittest
from blockchain import Block, Chain
from nipopow import NIPoPoW
from render import render

class TestBlockchain(unittest.TestCase):
    def test_block(self):
        G = Block.genesis()
        self.assertTrue(G.genesis)
        self.assertEqual(G.height, 0)

    def test_chain(self):
        G = Block.genesis()
        C = Chain()
        C.append(G)
        b = C.mine()
        self.assertEqual(len(C), 2)
        self.assertEqual(C[0], G)
        self.assertEqual(C[-1], b)
        self.assertEqual(C[0:2], C)
        self.assertEqual(len(C.slice(G, b)), 1)
        self.assertEqual(C[0].height, 0)
        self.assertEqual(C[1].height, 1)
        self.assertTrue(C.is_chained())

    def test_addressing(self):
        C = Chain(Block.genesis())
        for n in range(100):
            C.mine()
        self.assertEqual(C[-1].height, 100)

        self.assertEqual(C[3:13], C[3:7].union(C[7:13]))
        self.assertEqual(C[3:13], C[7:13].union(C[3:7]))
        self.assertNotEqual(C[3:13], C[7:12].union(C[3:7]))
        self.assertNotEqual(C[3:13], C[7:13].union(C[3:6]))

        self.assertEqual(C.union(C), C)
        self.assertEqual(C.intersect(C), C)

    def make_expected_distribution_superchain(self, length, interlink=False, gen=None):
        if gen is None:
            gen = Block.genesis()
        C = Chain(gen)
        for n in range(1, length + 1):
            C.mine()
            # expected distribution, OEIS A007814
            if n % 2 == 1:
                lvl = 0
            else:
                lvl = 1 + C[n // 2].level
            C[-1].level = lvl
            if interlink:
                C[-1].velvet_interlink = C[-1].real_interlink

        return C

    def test_interlink(self):
        C = self.make_expected_distribution_superchain(2**7)

        self.assertEqual(len(C[-1].real_interlink), 7)
        self.assertEqual(len(C.upchain(1)), 1 + len(C) // 2)
        self.assertEqual(len(C.upchain(2)), 1 + len(C) // 4)
        self.assertEqual(len(C.upchain(3)), 1 + len(C) // 8)
        self.assertEqual(C.count_upchain(1), 1 + len(C) // 2)
        self.assertEqual(C.count_upchain(2), 1 + len(C) // 4)
        self.assertEqual(C.count_upchain(3), 1 + len(C) // 8)
        self.assertEqual(C.upchain(0), C)

        self.assertEqual(C.upchain(3).upchain(3), C.upchain(3))
        self.assertTrue(C.upchain(3)[-1].level >= 3)

        self.assertEqual(C.upchain(4).intersect(C.upchain(3)), C.upchain(4))

        self.assertTrue(C.subchain(C))
        self.assertFalse(C.subchain(C[:-1]))
        self.assertTrue(C[:-1].subchain(C))

    def assertWins(self, proof1, proof2):
        self.assertTrue(proof1 >= proof2)
        self.assertFalse(proof2 >= proof1)

    def test_prove(self):
        C = self.make_expected_distribution_superchain(2**7, True)
        C.mine()

        k = 1
        m = 3
        proof = NIPoPoW.prove(k, m, C)
        pi, chi = proof.chain[:-k], proof.chain[-k:]
        self.assertEqual(pi.upchain(6), C[:-1].upchain(6))
        self.assertEqual(len(pi.upchain(6)), 3)
        self.assertEqual(len(pi.upchain(5)), 5)
        self.assertEqual(len(pi.upchain(4)), 7)
        self.assertEqual(len(pi - pi.upchain(1)), 2)
        # 3 blocks at level 6, including genesis
        # 2 new blocks at every subsequent level
        # 6 -> 3
        # 5 -> 2
        # 4 -> 2
        # 3 -> 2
        # 2 -> 2
        # 1 -> 2
        # 0 -> 2
        self.assertEqual(len(pi), 15)
        self.assertEqual(len(chi), 1)
        self.assertTrue(len(pi) >= m + k)
        self.assertTrue(pi.union(chi).subchain(C))

        self.assertTrue(proof >= proof)
        self.assertWins(
            NIPoPoW.prove(k, m, C), NIPoPoW.prove(k, m, C[:-1])
        )
        self.assertWins(
            NIPoPoW.prove(len(C) + 1, m, C), NIPoPoW.prove(len(C) + 1, m, C[:-1])
        )
        self.assertWins(
            NIPoPoW.prove(len(C) - 3, m, C), NIPoPoW.prove(len(C) - 3, m, C[:-1])
        )

    def test_verify(self):
        k = 1
        m = 3

        C = self.make_expected_distribution_superchain(2**7, True)
        fork_point = C[-1]

        C1 = self.make_expected_distribution_superchain(2**3, True, fork_point)
        C2 = self.make_expected_distribution_superchain(2**7, True, fork_point)

        self.assertTrue(C1.is_chained())
        self.assertTrue(C2.is_chained())

        proof1 = NIPoPoW.prove(k, m, C1)
        proof2 = NIPoPoW.prove(k, m, C2)

        self.assertTrue(proof1.chain.is_chained())
        self.assertTrue(proof2.chain.is_chained())

        self.assertWins(NIPoPoW.prove(k, m, C2), NIPoPoW.prove(k, m, C1))

    def test_at_correct_level(self):
        k = 1
        m = 3

        # both chains will compare at level 30
        # ensure there's at least m = 3 blocks of level 30
        G = Block.genesis()
        C1 = Chain(G)
        C2 = Chain(G)

        # C1 has 3 blocks at 30 and then 10+k blocks at 0
        for i in range(3):
            C1.mine()
            C1[-1].level = 30
        for i in range(10 + k):
            C1.mine()
            C1[-1].level = 0

        # C2 has 6 blocks at 30, then k blocks at 0
        for i in range(6):
            C2.mine()
            C2[-1].level = 30
        for i in range(k):
            C2.mine()
            C2[-1].level = 0

        # Ensure only blocks of the right level count
        proof1 = NIPoPoW.prove(k, m, C1)
        proof2 = NIPoPoW.prove(k, m, C2)
        b, (score1, mu1), (score2, mu2) = NIPoPoW.score(proof1, proof2)
        self.assertEqual(mu1, 30)
        self.assertEqual(mu2, 30)
        self.assertEqual(b, G)
        self.assertEqual(score1, 2**30 * 3)
        self.assertEqual(score2, 2**30 * 6)
        assert(len(C1) > len(C2))
        self.assertWins(proof2, proof1)

    def test_verify_inconsistency(self):
        k = 1
        m = 3

        C = self.make_expected_distribution_superchain(2**7, True)

        C1 = Chain(C[-1])
        for i in range(10):
            C1.mine()
            C1[-1].level = 30
        C2 = self.make_expected_distribution_superchain(2**7, True, C[-1])

        self.assertTrue(C1.is_chained())
        self.assertTrue(C2.is_chained())

        proof1 = NIPoPoW.prove(k, m, C1)
        proof2 = NIPoPoW.prove(k, m, C2)

        self.assertTrue(proof1.chain.is_chained())
        self.assertTrue(proof2.chain.is_chained())

        # a shorter chain with more superblocks wins
        # (this will never happen in practice for large values of m)
        self.assertWins(NIPoPoW.prove(k, m, C1), NIPoPoW.prove(k, m, C2))

    def test_nipopow(self):
        pass

if __name__ == '__main__':
    unittest.main()
