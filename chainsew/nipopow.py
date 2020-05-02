from blockchain import Chain

class NIPoPoW:
    @classmethod
    def prove(cls, k, m, C):
        proof = NIPoPoW(k=k, m=m)
        if len(C) <= k:
            proof.chain = C
            return proof

        chi = C[-k:]
        stable_C = C[:-k]
        pi = Chain()
        b = C[0]
        for mu in range(len(stable_C[-1].real_interlink) + 1, -1, -1):
            alpha = stable_C.slice(b).upchain(mu)
            pi |= alpha
            if len(alpha) > m:
                b = alpha[-m]

        proof.chain = pi | chi
        return proof
    
    @classmethod
    def score(cls, proof1, proof2):
        assert proof1.k == proof2.k and proof1.m == proof2.m, 'Proofs are incomparable'
        assert proof1.chain[0] == proof2.chain[0], 'Proofs must share a genesis block'
        
        k = proof1.k

        if len(proof1.chain) < k or len(proof2.chain) < k:
            # Comparison at the 0 level
            return proof1.chain[0], (len(proof1.chain), 0), (len(proof2.chain), 0)

        pi_1, chi_1 = proof1.chain[:-k], proof1.chain[-k:]
        pi_2, chi_2 = proof2.chain[:-k], proof2.chain[-k:]

        b = (pi_1 & pi_2)[-1]

        return b, proof1.best_arg(b), proof2.best_arg(b)

    def __init__(self, k, m):
        self.k = k
        self.m = m
        self.chain = Chain()

    def best_arg(self, b):
        k, m = self.k, self.m

        pi = self.chain[:-k]
        best_score = 0
        best_level = -1
        for mu in range(len(pi[-1].real_interlink) + 1):
            if len(pi.slice(b)[1:].upchain(mu)) >= m or mu == 0:
                mu_score = 2**mu * len(pi.slice(b)[1:].upchain(mu)) 
                if mu_score > best_score:
                    best_score = mu_score
                    best_level = mu
        return best_score, best_level
    
    def __ge__(self, other):
        if not self.chain.is_chained():
            return False
        if not other.chain.is_chained():
            return True

        score = NIPoPoW.score(self, other)
        b, data1, data2 = score
        b, (score1, mu1), (score2, mu2) = NIPoPoW.score(self, other)

        return score1 >= score2