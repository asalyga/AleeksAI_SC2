import sc2
import random
import time
from sc2 import run_game, maps, Race, Difficulty, position
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
import keras
#os.environ["SC2PATH"] = '/Applications/StarCraft2'

HEADLESS = False

class AleeksBot(sc2.BotAI):
    def __init__(self, use_model = False):
        self.ITERATION_PER_MINUTE = 165
        self.raw_affects_selection = True
        #self.unit_command_uses_self_do = True
        self.do_something_after = 0
        self.use_model = use_model
        self.train_data = []
        if self.use_model:
            print ("Using model")
            self.model = keras.models.load_model("BasicCNN")


    def on_end(self, game_result):
        print('--- on_end called ---')
        print(game_result, self.use_model)
        if game_result == game_result.Victory:
            np.save("train_data/{}.npy".format(str(int(time.time()))), np.array(self.train_data))

        with open("log.txt","a") as f:
            if self.use_model:
                f.write("Model {}\n".format(game_result))
            else:
                f.write("Random {}\n".format(game_result))

    

    async def on_step(self, interation):
        self.iteration = interation
        await self.scout()
        await self.distribute_workers()
        await self.build_workers()
        await self.build_pylons()
        await self.build_assimilators()
        await self.expand()
        await self.build_gateway_core_robo()
        await self.build_army()
        #await self.build_zealot()
        await self.attack()
        await self.chronoboost()
        await self.vision()
        await self.scout()


    async def vision(self):
        game_data = np.zeros((self.game_info.map_size[1],self.game_info.map_size[0], 3), np.uint8)
        draw_dic = {
            UnitTypeId.NEXUS : [15, (0, 255, 0)],
            UnitTypeId.PYLON : [3, (20, 235, 0)],
            UnitTypeId.PROBE : [1, (55, 200, 0)],
            UnitTypeId.ASSIMILATOR : [2, (55, 200, 0)],
            UnitTypeId.GATEWAY : [3, (200, 100, 0)],
            UnitTypeId.CYBERNETICSCORE : [3, (150, 150, 0)],
            UnitTypeId.STARGATE : [5, (255, 0, 0)],
            UnitTypeId.ROBOTICSFACILITY : [5, (215, 155, 0)],
            UnitTypeId.VOIDRAY : [3, (255, 100, 0)],
        }

        for unit_type in draw_dic:
           for unit in self.units(unit_type).ready or self.structures(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dic[unit_type][0], draw_dic[unit_type][1], -1)

        main_base_names = ["nexus", "supplydepot", "hatchery"]
        for enemy_building in self.enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() not in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)

        for enemy_building in self.enemy_structures:
            pos = enemy_building.position
            if enemy_building.name.lower() in main_base_names:
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (255, 0, 0), -1)

        for enemy_unit in self.enemy_units:
            if not enemy_unit.is_structure:
                worker_names = ["probe",
                                "scv",
                                "drone"]
                pos = enemy_unit.position
                if enemy_unit.name.lower() in worker_names:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
                else:
                    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 255), -1)

        for observer in self.units(UnitTypeId.OBSERVER).ready:
            pos = observer.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (225, 225, 225), -1)

        line_max = 50
        mineral_ratio = self.minerals/1500
        if mineral_ratio > 1.0:
            mineral_ratio = 1.0

        vespene_ratio = self.vespene/1500
        if vespene_ratio > 1.0:
            vespene_ratio = 1.0


        population_ratio = self.supply_left/self.supply_cap
        if population_ratio > 1.0:
            population_ratio = 1.0

        plausible_supply = self.supply_cap / 200.0


        military_weight = len(self.units(UnitTypeId.VOIDRAY)) / (self.supply_cap-self.supply_left)
        if military_weight > 1.0:
            military_weight = 1.0


        cv2.line(game_data, (0, 19), (int(line_max*military_weight), 19), (250, 250, 200), 3)
        cv2.line(game_data, (0, 13), (int(line_max*plausible_supply), 13), (220, 200, 200), 3)
        cv2.line(game_data, (0, 11), (int(line_max*population_ratio), 11), (150, 150, 150), 3)
        cv2.line(game_data, (0,  7), (int(line_max*vespene_ratio), 7), (210, 200, 0), 3)
        cv2.line(game_data, (0,  3), (int(line_max*mineral_ratio), 3), (0, 255, 25), 3)


        self.flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(self.flipped, dsize = None, fx = 3, fy = 3)
        cv2.imshow('vision', resized)
        cv2.waitKey(1)


    def random_location(self, enemy_start_locations):
        x = enemy_start_locations[0]
        y = enemy_start_locations[1]
        x += ((random.randrange(-20,20))/100) * enemy_start_locations[0]
        y += ((random.randrange(-20,20))/100) * enemy_start_locations[1]

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]
        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]
        
        go_to = position.Point2(position.Pointlike((x,y)))
        return go_to

    
    async def scout(self):
        if len(self.units(UnitTypeId.OBSERVER)) > 0:
            scout = self.units(UnitTypeId.OBSERVER)[0]
            if scout.is_idle:
                enemy_location = self.enemy_start_locations[0]
                move_to = self.random_location(enemy_location)
                print(move_to)
                scout.move(move_to)

        else:
            for rf in self.structures(UnitTypeId.ROBOTICSFACILITY).ready.idle:
                if self.can_afford(UnitTypeId.OBSERVER) and self.supply_left > 0:
                    rf.train(UnitTypeId.OBSERVER)


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
        if self.townhalls.amount  < 5 and not self.already_pending(UnitTypeId.NEXUS):
            if self.can_afford(UnitTypeId.NEXUS):
                await self.expand_now()


    async def build_gateway_core_robo(self):
        if self.structures(UnitTypeId.PYLON).ready.exists:
            pylon1 = self.structures(UnitTypeId.PYLON).ready.random


            if self.structures(UnitTypeId.GATEWAY).ready.exists and not self.structures(UnitTypeId.CYBERNETICSCORE):
                if self.can_afford(UnitTypeId.CYBERNETICSCORE) and not self.already_pending(UnitTypeId.CYBERNETICSCORE):
                    await self.build(UnitTypeId.CYBERNETICSCORE, near = pylon1)


            elif len(self.structures(UnitTypeId.GATEWAY)) < 1:
                if self.can_afford(UnitTypeId.GATEWAY) and not self.already_pending(UnitTypeId.GATEWAY):
                    await self.build(UnitTypeId.GATEWAY, near = pylon1)


            if self.structures(UnitTypeId.CYBERNETICSCORE).ready.exists:
                if len(self.units(UnitTypeId.STARGATE)) < 5:
                    if len(self.units(UnitTypeId.STARGATE)) < ((self.iteration*3)/self.ITERATION_PER_MINUTE):
                        if self.can_afford(UnitTypeId.STARGATE) and not self.already_pending(UnitTypeId.STARGATE):
                            await self.build(UnitTypeId.STARGATE, near = pylon1)


            if self.structures(UnitTypeId.CYBERNETICSCORE).ready.exists:
                if len(self.structures(UnitTypeId.ROBOTICSFACILITY)) < 1:
                    if self.can_afford(UnitTypeId.ROBOTICSFACILITY) and not self.already_pending(UnitTypeId.ROBOTICSFACILITY):
                        await self.build(UnitTypeId.ROBOTICSFACILITY, near = pylon1)


    async def build_army(self):
        """if self.units(UnitTypeId.STALKER).amount < 13:
            for gateway1 in self.structures(UnitTypeId.GATEWAY).ready.idle:
                #if not self.units(UnitTypeId.STALKER).amount > self.units(UnitTypeId.VOIDRAY).amount:
                    if self.can_afford(UnitTypeId.STALKER) and self.supply_left > 2:
                        gateway1.train(UnitTypeId.STALKER)
        """
        if self.units(UnitTypeId.VOIDRAY).amount < 10:
            for stargate in self.structures(UnitTypeId.STARGATE).ready.idle:
                if self.can_afford(UnitTypeId.VOIDRAY) and self.supply_left > 0:
                    stargate.train(UnitTypeId.VOIDRAY)


    """ async def build_zealot(self):
        if self.structures(UnitTypeId.GATEWAY) and not self.structures(UnitTypeId.CYBERNETICSCORE).ready:
            for gateway1 in self.structures(UnitTypeId.GATEWAY).ready.idle:
                if self.can_afford(UnitTypeId.ZEALOT) and self.supply_left > 1:
                    gateway1.train(UnitTypeId.ZEALOT)
    """

    def find_enemy(self, state):
        if len(self.enemy_units) > 0:
            return random.choice(self.enemy_units)
        elif len(self.enemy_structures) > 0:
            return random.choice(self.enemy_structures)
        else:
            return self.enemy_start_locations[0]



    async def attack(self):
        if len(self.units(UnitTypeId.VOIDRAY).idle) > 0:
            #choice = random.randrange(0, 4)
            target = False
            if self.iteration > self.do_something_after:
                if self.use_model:
                    prediction = self.model.predict([self.flipped.reshape([-1, 176, 200, 3])])
                    choice = np.argmax(prediction[0])

                    choice_dict = {0: "No Attack!",
                                  1: "Attack close to our nexus!",
                                  2: "Attack Enemy Structure!",
                                  3: "Attack Eneemy Start!"}

                    print("Choice #{}:{}".format(choice, choice_dict[choice]))

                else:
                    choice = random.randrage(0, 4)

                """if choice == 0:
                    #dont attack
                    wait = random.randrange(20, 165)
                    self.do_something_after = self.iteration + wait
                
                elif choice == 1:
                    #attack closets units to our nexuses
                    if len(self.enemy_units) > 0:
                        target = self.enemy_units.closest_to(random.choice(self.structures(UnitTypeId.NEXUS)))

                elif choice == 2:
                    if len(self.enemy_structures) > 0:
                        target = random.choice(self.enemy_structures)

                elif choice == 3:
                    #attack enemy startig location
                    target = self.enemy_start_locations[0]

                if target:
                    for vr in self.units(UnitTypeId.VOIDRAY).idle:
                        self.do(vr.attack(target))

                y = np.zeros(4)
                y[choice] = 1
                print(y)
                self.train_data.append([y, self.flipped])"""
                
              
    async def chronoboost(self):
        if self.townhalls.exists:
            nexus = self.structures(UnitTypeId.NEXUS).ready.random
            if not nexus.is_idle and not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                nexuses = self.structures(UnitTypeId.NEXUS)
                abilities = await self.get_available_abilities(nexuses)
                for loop_nexus, abilities_nexus in zip(nexuses, abilities):
                    if AbilityId.EFFECT_CHRONOBOOSTENERGYCOST in abilities_nexus:
                        loop_nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
                        break

    
map_pool = [
    "AbyssalReefLE", "BelShirVestigeLE",
    "CactusValleyLE", "ProximaStationLE", 
    "NewkirkPrecinctTE", "PaladinoTerminalLE"
    ]

playing_map = random.choice(map_pool)

run_game(
    sc2.maps.get(playing_map),
    [
    Bot(sc2.Race.Protoss, AleeksBot(use_model = True)), 
    Computer(sc2.Race.Terran, sc2.Difficulty.Medium)
    ],
    realtime = True
)