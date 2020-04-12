import sc2
import random
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class AleeksBot(sc2.BotAI):
    def __init__(self):
        self.raw_affects_selection = True


    async def on_step(self, interation):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.build_assimilators()
        await self.expand()
        await self.build_gateway_core()
        await self.build_stalker()
    

    async def build_workers(self):
        for town_halls in self.townhalls.idle:
            if self.can_afford(UnitTypeId.PROBE):
                town_halls.train(UnitTypeId.PROBE)
            else:
                break


    async def build_pylons(self):
        if self.supply_left < 7 and not self.already_pending(UnitTypeId.PYLON):
            nexuses = self.townhalls.ready
            if nexuses.exists:
                if self.can_afford(UnitTypeId.PYLON):
                    await self.build(UnitTypeId.PYLON, near = nexuses.first)


    async def build_assimilators(self):
        if self.supply_used > 20 and not self.already_pending(UnitTypeId.ASSIMILATOR):
            for town_halls1 in self.townhalls.ready:
                vespenes = self.vespene_geyser.closer_than(10, town_halls1)
                for vespene in vespenes:
                    if not self.can_afford(UnitTypeId.ASSIMILATOR):
                        break
                    worker = self.select_build_worker(vespene.position)
                    if worker is None:
                        break
                    if not self.units(UnitTypeId.ASSIMILATOR).closer_than(1.0, vespenes).exists:
                        worker.build(UnitTypeId.ASSIMILATOR, vespene)


    async def expand(self):
        if self.townhalls.amount  < 3 and not self.already_pending(UnitTypeId.NEXUS):
            if self.can_afford(UnitTypeId.NEXUS):
                await self.expand_now()


    async def build_gateway_core(self):
        if self.units(UnitTypeId.PYLON).ready.exists:
            pylon1 = self.units(UnitTypeId.PYLON).ready.random
            if self.units(UnitTypeId.GATEWAY).ready.exists:
                if not self.units(UnitTypeId.CYBERNETICSCORE):
                    if self.can_afford(UnitTypeId.CYBERNETICSCORE) and not self.already_pending(UnitTypeId.CYBERNETICSCORE):
                        await self.build(UnitTypeId.CYBERNETICSCORE, near = pylon1)
            else:
                if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                    await self.build(UnitTypeId.GATEWAY, near = pylon1)

                  


    async def build_stalker(self):
        for gateway1 in self.units(UnitTypeId.GATEWAY).ready.idle:
            if self.can_afford(UnitTypeId.STALKER) and self.supply_left > 0:
                gateway1.train(UnitTypeId.STALKER)





    



run_game(
    sc2.maps.get("AbyssalReefLE"),
    [Bot(sc2.Race.Protoss, AleeksBot()), Computer(sc2.Race.Terran, sc2.Difficulty.Easy)],
    realtime = False,
)