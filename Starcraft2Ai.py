import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *

class AleeksBot(sc2.BotAI):
    async def on_Step(self, iteration):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.build_assimilators()
        await self.expand()



    async def build_workers(self):
        for nexus in self.units(nexus).ready.noqueue:
            if self.can_afford(nexus):
                await self.do(nexus.train(probe))

    async def build_pylons(self):
        if self.supply_left<5 and not self.already_pending(pylon):
            nexuses = self.units(nexus).ready
            if nexuses.exists:
                if self.can_afford(pyolon):
                    await self.build(pylon, near=nexuses.first)

    async def build_assimilators(self):
        for nexus in self.units(nexus).ready:
            vaspenes = self.state.vespene_geyser.closer_than(10, nexus)
            for vaspene in vaspenes:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).cloaser_than(1.0, vaspene).exists:
                    await self.do(worker.build(ASSIMILATOR, vaspene))

    async def expand(self):
        if self.units(NEXUS).amount < 3 and not self.already_pending(NEXUS):
            if self.can_afford(NEXUS):
                await self.expand_now()




run_game(maps.get("AbyssalReefLE"),
    [
    Bot(Race.Protoss, AleeksBot()),
    Computer(Race.Terran, Difficulty.Easy)
    ], realtime=True)