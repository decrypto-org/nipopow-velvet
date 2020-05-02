from blockchain import Block, Chain
from nipopow import NIPoPoW
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
    # First, create a block that performs a double spend, which extends genesis.
    # This block, the double_spend_block, will be withheld and never adopted by the honest parties.
    DOUBLE_SPEND = 1
    # Then, create a block stitch_block that has a previd pointer to the honest chain, but a thorny
    # interlink pointer to the double_spend_block. The honest parties will adopt this.
    STITCH = 2
    # Allow the chain to grow, usurping blocks from the honest chain, but bypassing honest blocks
    # that are of high level. These blocks are bypassed by creating a block that has an (direct or indirect)
    # previd pointer to them, but a thorny interlink pointer to their last low-level ancestor.
    # We need to bypass them so that they are not used as the LCA block between the adversarial
    # and honest NIPoPoWs.
    GROW = 3
    # Once the honest chain has 2m blocks at every level below mu_B and sufficient blocks
    # at every level so that our bypassing was adequate, start growing an independent k-length
    # 0-level suffix.
    SUFFIX = 4
    # Once the suffix is completed, mining is done and we can create the adversarial NIPoPoW.
    DONE = 5

class Adversary(Party):
    def __init__(self, genesis, k, m, mu_B):
        self.attack_phase = AttackPhase.DOUBLE_SPEND
        self.m = m
        self.k = k
        self.mu_B = mu_B
        self.bypass_level = mu_B
        self.bypass_level_blocks_seen = 0
        self.min_bypass_level = 2
        self.honest_chain = Chain(genesis)
        self.last_good_honest_block = None
        self.double_spend_block = None
        self.stitch_block = None
        self.blocks_mined = []
        self.need_bypass = False
        self.adversarial_nipopow = NIPoPoW(k, m)
        self.adversarial_nipopow.chain.append(genesis)

        super().__init__(genesis)

    def play(self):
        if self.attack_phase == AttackPhase.DOUBLE_SPEND:
            self.double_spend_block = self.chain.mine(True)
            self.blocks_mined.append(self.double_spend_block)
            self.adversarial_nipopow.chain.append(self.double_spend_block)
            self.attack_phase = AttackPhase.STITCH

            return None # withhold double spending block

        if self.attack_phase == AttackPhase.STITCH:
            self.stitch_block = self.honest_chain.mine(True)
            self.stitch_block.set_thorny_interlink([self.double_spend_block])
            self.last_good_honest_block = self.stitch_block
            self.blocks_mined.append(self.stitch_block)
            self.adversarial_nipopow.chain.append(self.stitch_block)
            self.attack_phase = AttackPhase.GROW

            return self.stitch_block
        
        if self.attack_phase == AttackPhase.GROW:
            discard = True
            if self.need_bypass:
                b = Block.mine(self.honest_chain[-1])
                b.adversarial = True
                b.set_thorny_interlink([self.last_good_honest_block])
                self.blocks_mined.append(b)
                if b.level < self.bypass_level:
                    # Our block is of low enough level to stay under the radar
                    # so we can use it for bypassing
                    # Bypass any blocks between last_good_honest_block and b,
                    # as they are blocks of a higher level than what we want.
                    self.last_good_honest_block = b
                    self.honest_chain.append(b)
                    self.adversarial_nipopow.chain.append(b)
                    # Bypass was successful.
                    self.need_bypass = False
                    discard = False
                else:
                    # Unfortunately, we mined a block of high level and this
                    # cannot be used for bypassing (as b would then be included
                    # by the honest prover into their proof), so we have to discard
                    # this block and try again
                    discard = True

            if not discard:
                return b
        
        if self.attack_phase == AttackPhase.SUFFIX:
            b = self.chain.mine(True)
            self.blocks_mined.append(b)
            self.adversarial_nipopow.chain.append(b)
            self.suffix_size += 1
            if self.suffix_size >= k and self.growth_completed():
                self.attack_phase = AttackPhase.DONE
            
            return None # withhold suffix
  
    def block_arrival(self, block):
        if self.attack_phase > AttackPhase.STITCH and self.attack_phase < AttackPhase.SUFFIX:
            if block.level >= self.bypass_level:
                # A superblock has appeared which is of higher level than we want.
                # We need to bypass it.
                # (There could be multiple of these in a row)
                self.need_bypass = True
                self.bypass_level_blocks_seen += 1
                if self.bypass_level_blocks_seen >= m:
                    self.bypass_level -= 1
                    self.bypass_level_blocks_seen = 0
                    if self.bypass_level < self.min_bypass_level:
                        self.attack_phase = AttackPhase.SUFFIX
                        self.chain = Chain(self.last_good_honest_block)
                        self.suffix_size = 0
            else:
                if not self.need_bypass:
                    self.last_good_honest_block = block
                    self.adversarial_nipopow.chain.append(block)

        self.honest_chain = Chain(block)

    def growth_completed(self):
        m = self.m
        mu_B = self.mu_B
        C = self.honest_chain.slice(self.stitch_block)
        if len(C.upchain(mu_B)) < 2*m:
            return False
        b = C[0]
        for mu in range(mu_B - 1, 0, -1):
            b = C.slice(b).upchain(mu + 1)[m]
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
    MONTE_CARLO_COUNT = 100
    adversarial_victories = 0

    for i in range(MONTE_CARLO_COUNT):
        G = Block.genesis()
        honest = Honest(G)
        adversary = Adversary(G, k, m, mu_B)

        while not adversary.ready():
            r = random()
            adversary_turn = (r < t / n)
            if adversary_turn:
                b = adversary.play()
                if b is not None:
                    honest.block_arrival(b)
            else:
                b = honest.play()
                adversary.block_arrival(b)
        honest_proof = NIPoPoW.prove(k, m, honest.chain)
        b, (score1, mu1), (score2, mu2) = NIPoPoW.score(honest_proof, adversary.adversarial_nipopow)
        # print('LCA = ', b)
        # print('Honest score = ', score1, ' (at level mu=', mu1, ')')
        # print('Adversarial score = ', score2, ' (at level mu=', mu2, ')')
        if honest_proof >= adversary.adversarial_nipopow:
            # print('Honest wins')
            pass
        else:
            # print('Adversary wins')
            adversarial_victories += 1
        # render(set(honest.chain) | set(adversary.blocks_mined),
        #     highlights=[('#4a86e8ff', honest_proof.chain)],
        #     show_interlinks=False)
    print('Pr[attack succeeds] ~=', adversarial_victories / MONTE_CARLO_COUNT)