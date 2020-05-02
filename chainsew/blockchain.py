from random import random
from collections import defaultdict
from copy import copy

class Block:
    global_id = 0

    @classmethod
    def mine(cls, prev, velvet=True):
        b = Block(prev)
        b.height = prev.height + 1
        b.calculate_level()
        b.calculate_interlink()
        if velvet:
            b.velvet = True
            b.velvet_interlink = b.real_interlink

        return b

    @classmethod
    def genesis(cls):
        G = Block(None)
        G.real_interlink = [G] # never overwritten
        G.level = 0
        G.genesis = True
        G.height = 0
        return G
    
    def set_thorny_interlink(self, thorny_interlink=None):
        assert self.adversarial, 'Honest blocks cannot be thorny'

        self.velvet_interlink = thorny_interlink
        self.thorny = True
        self.velvet = True

    def calculate_level(self):
        while True:
            r = random()
            if r < 0.5:
                break
            self.level += 1

    def calculate_interlink(self):
        self.real_interlink = copy(self.prev.real_interlink)
        for mu in range(1, self.prev.level + 1):
            if mu >= len(self.real_interlink):
                self.real_interlink.append(None)
            self.real_interlink[mu] = self.prev

    def ancestors(self):
        b = self
        ret = [b]
        while b.prev is not None:
            b = b.prev
            ret.append(b)
        return ret

    def __init__(self, prev):
        self.level = 0
        self.prev = prev
        self.genesis = False
        self.thorny = False
        self.velvet = False
        self.adversarial = False
        self.velvet_interlink = None
        self.id = Block.global_id
        Block.global_id += 1

    def __repr__(self):
        block_data = [str(self.id)]
        block_data.append("mu=" + str(self.level))
        if self.genesis:
            block_data.append('(gen)')
        if self.adversarial:
            block_data.append('(adv)')
        return '<Block ' + ' '.join(block_data) + '>'

class Chain:
    @classmethod
    def from_block_set(cls, blocks):
        ret = cls()
        ret.replace_blocks_with(blocks)
        return ret

    def replace_blocks_with(self, blocks):
        self.blocks = list(blocks)
        self.blocks.sort(key=lambda b: b.id)

    def __init__(self, genesis=None):
        self.blocks = []
        if genesis is not None:
            assert isinstance(genesis, Block), 'A chain must extend a block'
            self.replace_blocks_with(genesis.ancestors())

    def append(self, block):
        self.blocks.append(block)

    def mine(self, adversarial=False):
        b = Block.mine(self[-1])
        b.adversarial = adversarial
        self.blocks.append(b)
        return b

    def __getitem__(self, key):
        if isinstance(key, slice):
            c = self.__class__()
            c.blocks = self.blocks[key]
            return c
        return self.blocks[key]

    def __eq__(self, other):
        return self.blocks == other.blocks

    def slice(self, blockA=None, blockZ=None):
        if blockA is None and blockZ is None:
            ret = self.__class__()
            ret.blocks = copy(self.blocks)
            return ret
        if blockA is not None:
            a = self.blocks.index(blockA)
            if blockZ is None:
                return self[a:]
        if blockZ is not None:
            z = self.blocks.index(blockZ)
            if blockA is None:
                return self[:z]
        return self[a:z]

    def __len__(self):
        return len(self.blocks)

    def upchain(self, mu):
        return self.filter(lambda b: b.level >= mu or b.genesis)

    def filter(self, f):
        ret = self.__class__()
        ret.blocks = list(filter(f, self.blocks))
        return ret

    def union(self, other):
        return self.__class__.from_block_set(set(self.blocks) | set(other.blocks))

    def intersect(self, other):
        return self.__class__.from_block_set(set(self.blocks) & set(other.blocks))

    def minus(self, other):
        return self.__class__.from_block_set(set(self.blocks) - set(other.blocks))

    def __or__(self, other):
        return self.union(other)

    def __and__(self, other):
        return self.intersect(other)

    def __sub__(self, other):
        return self.minus(other)

    def subchain(self, other):
        i = 0
        for block in self.blocks:
            while i < len(other.blocks):
                if other.blocks[i] == block:
                    break
                i += 1
            else:
                return False
        return True

    def is_chained(self):
        for prev_block, block in zip(self.blocks, self.blocks[1:]):
            if prev_block == block.prev:
                continue
            if block.velvet_interlink is not None:
                if prev_block in block.velvet_interlink:
                    continue
            return False
        return True

    def __repr__(self):
        repr = ['Chain of blocks: ']
        for block in self.blocks:
            repr.append('\t' + str(block))
        return '\n'.join(repr)

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

    def __init__(self, **kwargs):
        self.k = kwargs['k']
        self.m = kwargs['m']
        self.chain = Chain()

    def best_arg(self, b):
        k, m = self.k, self.m

        pi = self.chain[:-k]
        best_score = 0
        for mu in range(len(pi[-1].real_interlink) + 1):
            if len(pi.slice(b).upchain(mu)) >= m or mu == 0:
                best_score = max(best_score, 2**mu * len(pi.slice(b)))
        return best_score

    def __ge__(self, other):
        assert self.k == other.k and self.m == other.m, 'Proofs are incomparable'
        
        k = self.k

        if not self.chain.is_chained():
            return False
        if not other.chain.is_chained():
            return True
        if len(self.chain) < k or len(other.chain) < k:
            return len(self.chain) >= len(other.chain)

        pi_1, chi_1 = self.chain[:-k], self.chain[-k:]
        pi_2, chi_2 = other.chain[:-k], other.chain[-k:]

        b = (pi_1 & pi_2)[-1]

        return self.best_arg(b) >= other.best_arg(b)
