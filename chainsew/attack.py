from blockchain import Block, Chain
from random import random
from render import render
from enum import IntEnum

class Party:
    def __init__(self, genesis):
        self.chain = Chain(genesis)
    
    def block_arrival(self, block):
        if block.height > self.chain[-1].height:
            self.chain = Chain(block)

    def play(self):
        return self.chain.mine()

class AttackPhase(IntEnum):
    DOUBLE_SPEND = 1
    STITCH = 2
    GROW = 3
    SUFFIX = 4
    DONE = 5

class Adversary(Party):
    def __init__(self, genesis, m, k, mu_B):
        self.attack_phase = AttackPhase.DOUBLE_SPEND
        self.m = m
        self.k = k
        self.mu_B = mu_B
        self.honest_chain = Chain(genesis)
        self.double_spend_block = None
        self.stitch_block = None
        self.blocks_mined = []

        super().__init__(genesis)

    def play(self):
        if self.attack_phase == AttackPhase.DOUBLE_SPEND:
            self.double_spend_block = self.chain.mine(True)
            self.blocks_mined.append(self.double_spend_block)
            self.attack_phase = AttackPhase.STITCH

            return None # withhold double spending block

        if self.attack_phase == AttackPhase.STITCH:
            self.stitch_block = self.honest_chain.mine(True)
            self.stitch_block.set_thorny_interlink([self.double_spend_block])
            self.blocks_mined.append(self.stitch_block)
            self.attack_phase = AttackPhase.GROW

            return self.stitch_block
        
        if self.attack_phase == AttackPhase.GROW:
            b = self.honest_chain.mine(True)
            self.blocks_mined.append(b)

            if self.growth_completed():
                self.attack_phase = AttackPhase.SUFFIX
                self.chain = Chain(self.honest_chain[-1])
                self.suffix_size = 0

            return b
        
        if self.attack_phase == AttackPhase.SUFFIX:
            b = self.chain.mine(True)
            self.blocks_mined.append(b)
            self.suffix_size += 1
            if self.suffix_size >= k:
                self.attack_phase = AttackPhase.DONE
            
            return None # withhold suffix
  
    def block_arrival(self, block):
        self.honest_chain = Chain(block)

    def growth_completed(self):
        m = self.m
        mu_B = self.mu_B
        C = self.honest_chain
        if len(C.upchain(mu_B)) < 2*m:
            return False
        # print('###')
        b = C[0]
        for mu in range(mu_B - 1, 0, -1):
            b = C.slice(b).upchain(mu + 1)[m]
            # print('Slicing point for level ' + str(mu + 1) + ' is ' + str(b))
            if len(C.slice(b).upchain(mu)) < 2*m:
                return False
        return True
    
    def ready(self):
        return self.attack_phase == AttackPhase.DONE

class Honest(Party):
    pass

if __name__ == '__main__':
    t = 1
    n = 5
    m = 3
    k = 3
    mu_B = 4

    G = Block.genesis()
    honest = Honest(G)
    adversary = Adversary(G, m, k, mu_B)

    while not adversary.ready():
        r = random()
        adversary_turn = (r < t / n)
        if adversary_turn:
            b = adversary.play()
            if b is not None:
                honest.block_arrival(b)
            # if adversary_prev_tip == G:
            #     double_spend_block = Block.mine(adversary_prev_tip)
        else:
            b = honest.play()
            adversary.block_arrival(b)
            # if b.level < mu_B and double_spend_confirmed:
            #     adversary_tip = b
            # if len(honest_chain.upchain(mu_B)) >= m:
            #     mu_B -= 1
    render(set(honest.chain) | set(adversary.blocks_mined), False)
