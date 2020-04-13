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
        await self.build_zealot()
        await self.attack()


    async def build_workers(self):
        amountTownHalls = self.townhalls.ready.amount
        amountProbes = self.units(UnitTypeId.PROBE).amount
        if amountProbes < (22*amountTownHalls) and not self.already_pending(UnitTypeId.PROBE):
            for town_halls in self.townhalls.idle:
                if self.can_afford(UnitTypeId.PROBE):
                    town_halls.train(UnitTypeId.PROBE)
                else:
                    break


    async def build_pylons(self):
        if self.supply_left < 3 and not self.already_pending(UnitTypeId.PYLON):
            nexuses = self.townhalls.ready
            if nexuses.exists:
                if self.can_afford(UnitTypeId.PYLON):
                    await self.build(UnitTypeId.PYLON, near = nexuses.first)


    async def build_assimilators(self):
        if self.supply_used > 15 and not self.already_pending(UnitTypeId.ASSIMILATOR):
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
        if self.structures(UnitTypeId.PYLON).ready.exists:
            pylon1 = self.structures(UnitTypeId.PYLON).ready.random
            if self.structures(UnitTypeId.GATEWAY).ready.exists and not self.structures(UnitTypeId.CYBERNETICSCORE):
                if self.can_afford(UnitTypeId.CYBERNETICSCORE) and not self.already_pending(UnitTypeId.CYBERNETICSCORE):
                    await self.build(UnitTypeId.CYBERNETICSCORE, near = pylon1)

            elif len(self.structures(UnitTypeId.GATEWAY)) < 3:
                if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                    await self.build(UnitTypeId.GATEWAY, near = pylon1)


    async def build_stalker(self):
        for gateway1 in self.structures(UnitTypeId.GATEWAY).ready.idle:
            if self.can_afford(UnitTypeId.STALKER) and self.supply_left > 2:
                gateway1.train(UnitTypeId.STALKER)


    async def build_zealot(self):
        if self.structures(UnitTypeId.GATEWAY) and not self.structures(UnitTypeId.CYBERNETICSCORE).ready:
            for gateway1 in self.structures(UnitTypeId.GATEWAY).ready.idle:
                if self.can_afford(UnitTypeId.ZEALOT) and self.supply_left > 1:
                    gateway1.train(UnitTypeId.ZEALOT)


    def find_enemy(self, state):
        if len(self.enemy_units) > 0:
            return random.choice(self.enemy_units)
        elif len(self.enemy_structures) > 0:
            return random.choice(self.enemy_structures)
        else:
            return self.enemy_start_locations[0]


    async def attack(self):
        if self.units(UnitTypeId.STALKER).amount > 15:
            for s in self.units(UnitTypeId.STALKER).idle:
                s.attack(self.find_enemy(self.state))

        if self.units(UnitTypeId.STALKER).amount > 5:
            if len(self.enemy_units) > 0:
                for s in self.units(UnitTypeId.STALKER).idle:
                    s.attack(random.choice(self.enemy_units))
            
                

    






    



run_game(
    sc2.maps.get("AbyssalReefLE"),
    [Bot(sc2.Race.Protoss, AleeksBot()), Computer(sc2.Race.Zerg, sc2.Difficulty.Easy)],
    realtime = False,
)