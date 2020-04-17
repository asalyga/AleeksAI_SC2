import sc2
import random
from sc2 import run_game, maps, Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.buff_id import BuffId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.buff_id import BuffId
from sc2.player import Bot, Computer
import cv2 as cv2
import numpy as np



class AleeksBot(sc2.BotAI):
    def __init__(self):
        self.ITERATION_PER_MINUTE = 165
        self.raw_affects_selection = True


    async def on_step(self, interation):
        self.iteration = interation
        await self.scout()
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.build_assimilators()
        await self.expand()
        await self.build_gateway_core()
        await self.build_stalker()
        #await self.build_zealot()
        await self.attack()
        await self.chronoboost()
        await self.intel()

    async def scout(self):
        if len(self.units(UnitTypeId.OBSERVER)) > 0:
            scout = self.units(UnitTypeId.OBSERVER)[0]
            if scout.is_idle:
                enemy_location = self.enemy_start_locations[0]
                move_to = enemy_location.random
                print(move_to)
                scout.move(move_to)

        else:
            for rf in self.structures(UnitTypeId.ROBOTICSFACILITY).ready.idle:
                if self.can_afford(UnitTypeId.OBSERVER) and self.supply_left > 0:
                    rf.train(UnitTypeId.OBSERVER)





    async def intel(self):
        game_data = np.zeros((self.game_info.map_size[1],self.game_info.map_size[0], 3), np.uint8)

        draw_dic = {
            UnitTypeId.NEXUS : [15, (0, 255, 0)],
            UnitTypeId.PYLON : [3, (20, 235, 0)],
            UnitTypeId.PROBE : [1, (55, 200, 0)],
            UnitTypeId.ASSIMILATOR : [2, (55, 200, 0)],
            UnitTypeId.GATEWAY : [3, (200, 100, 0)],
            UnitTypeId.CYBERNETICSCORE : [3, (150, 150, 0)],
            UnitTypeId.STARGATE : [5, (255, 0, 0)],
            UnitTypeId.VOIDRAY : [3, (255, 100, 0)],
        }



        for unit_type in draw_dic:
           for unit in self.units(unit_type).ready or self.structures(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dic[unit_type][0], draw_dic[unit_type][1], -1)

        flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(flipped, dsize = None, fx = 3, fy = 3)
        cv2.imshow('Intel', resized)
        cv2.waitKey(1)


    async def build_workers(self):
        CurrentAmountHalls = self.townhalls.ready.amount
        CurrentProbes = self.workers.amount
        MaxProbes = (22*CurrentAmountHalls)-2
        if not self.already_pending(UnitTypeId.PROBE) and (CurrentProbes < MaxProbes):
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

            elif len(self.structures(UnitTypeId.GATEWAY)) < 1:
                if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                    await self.build(UnitTypeId.GATEWAY, near = pylon1)

            if self.structures(UnitTypeId.CYBERNETICSCORE).ready.exists:
                if len(self.units(UnitTypeId.STARGATE)) < (self.iteration/self.ITERATION_PER_MINUTE):
                    if self.can_afford(UnitTypeId.STARGATE) and not self.already_pending(UnitTypeId.STARGATE):
                        await self.build(UnitTypeId.STARGATE, near = pylon1)


    async def build_stalker(self):
        #for gateway1 in self.structures(UnitTypeId.GATEWAY).ready.idle:
        #    if not self.units(UnitTypeId.STALKER).amount > self.units(UnitTypeId.VOIDRAY).amount:
        #        if self.can_afford(UnitTypeId.STALKER) and self.supply_left > 2:
        #            gateway1.train(UnitTypeId.STALKER)

        for stargate in self.structures(UnitTypeId.STARGATE).ready.idle:
            if self.can_afford(UnitTypeId.VOIDRAY) and self.supply_left > 0:
                stargate.train(UnitTypeId.VOIDRAY)


    #async def build_zealot(self):
    #    if self.structures(UnitTypeId.GATEWAY) and not self.structures(UnitTypeId.CYBERNETICSCORE).ready:
    #        for gateway1 in self.structures(UnitTypeId.GATEWAY).ready.idle:
    #            if self.can_afford(UnitTypeId.ZEALOT) and self.supply_left > 1:
    #                gateway1.train(UnitTypeId.ZEALOT)


    def find_enemy(self, state):
        if len(self.enemy_units) > 0:
            return random.choice(self.enemy_units)
        elif len(self.enemy_structures) > 0:
            return random.choice(self.enemy_structures)
        else:
            return self.enemy_start_locations[0]



    async def attack(self):
        # {UNIT: [n to fight, n to defend]}
        aggressive_units = {
                            #UnitTypeId.STALKER: [15, 1],
                            UnitTypeId.VOIDRAY: [8, 1],
                            }


        for UNIT in aggressive_units:
            if self.units(UNIT).amount > aggressive_units[UNIT][0] and self.units(UNIT).amount > aggressive_units[UNIT][1]:
                for s in self.units(UNIT).idle:
                    self.do(s.attack(self.find_enemy(self.state)))
                    #await self.do(s.attack(self.find_enemy(self.state)))

            elif self.units(UNIT).amount > aggressive_units[UNIT][1]:
                if len(self.enemy_units) > 0:
                    for s in self.units(UNIT).idle:
                        self.do(s.attack(random.choice(self.enemy_units)))
                        #await self.do(s.attack(random.choice(self.known_enemy_units)))

    #async def attack(self):
    #    if self.units(UnitTypeId.STALKER).amount > 15:
    #        for s in self.units(UnitTypeId.STALKER).idle:
    #            s.attack(self.find_enemy(self.state))

    #    if self.units(UnitTypeId.STALKER).amount > 5:
    #        if len(self.enemy_units) > 0:
    #            for s in self.units(UnitTypeId.STALKER).idle:
    #                s.attack(random.choice(self.enemy_units))
            
                
    async def chronoboost(self):
        nexus = self.townhalls.ready.random
        if not nexus.is_idle and not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
            nexuses = self.structures(UnitTypeId.NEXUS)
            abilities = await self.get_available_abilities(nexuses)
            for loop_nexus, abilities_nexus in zip(nexuses, abilities):
                if AbilityId.EFFECT_CHRONOBOOSTENERGYCOST in abilities_nexus:
                    loop_nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
                    break

    
map_pool = [
    "AbyssalReefLE", "BelShirVestigeLE",
    "CactusValleyLE", "HonorgroundsLS", 
    "NewkirkPrecinctTE", "PaladinoTerminalLE",
    "ProximaStationLE"
    ]

playing_map = random.choice(map_pool)

run_game(
    sc2.maps.get(playing_map),
    [
    Bot(sc2.Race.Protoss, AleeksBot()), 
    Computer(sc2.Race.Terran, sc2.Difficulty.Hard)
    ],
    realtime = False,
)