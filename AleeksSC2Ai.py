import sc2
import random
import cv2
import numpy as np
import time
import math
import keras

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

# os.environ["SC2PATH"] = '/Applications/StarCraft2'

HEADLESS = False


class AleeksBot(sc2.BotAI):
    def __init__(self, use_model=False, title=1):
        self.raw_affects_selection = True
        self.train_data = []
        self.use_model = use_model
        self.title = title
        self.do_something_after = 0
        self.scouts_and_spots = {}

        self.choices = {
            0: self.build_scout,
            1: self.build_zealot,
            2: self.build_gateway,
            3: self.build_stalker,
            4: self.build_voidray,
            5: self.build_workers,
            6: self.build_assimilators,
            7: self.build_stargate,
            8: self.build_pylons,
            9: self.defend_nexus,
            10: self.attack_known_enemy_unit,
            11: self.attack_known_enemy_structure,
            12: self.expand,
            13: self.do_nothing,
        }

        self.train_data = []
        if self.use_model:
            print("Using model")
            self.model = keras.models.load_model("TrainedData")

    def on_end(self, game_result):
        print('--- on_end called ---')
        print(game_result, self.use_model)

        # if game_result == game_result.Victory:
        #    np.save("train_data/{}.npy".format(str(int(time.time()))), np.array(self.train_data))

        with open("gameout-random-vs-medium.txt", "a") as f:
            if self.use_model:
                f.write("Model {}\n".format(game_result))
            else:
                f.write("Random {}\n".format(game_result))

    async def on_step(self, interation):

        self.GameTime = (self.state.game_loop / 22.4) / 60
        print('Time:', self.GameTime)
        await self.distribute_workers()
        await self.scout()
        await self.vision()
        await self.do_something()
        await self.chronoboost()

    def random_location(self, location):
        x = location[0]
        y = location[1]

        x += random.randrange(-5, 5)
        y += random.randrange(-5, 5)

        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]

        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]

        go_to = position.Point2(position.Pointlike((x, y)))
        return go_to

    async def scout(self):
        self.expand_dis_dir = {}
        for el in self.expansion_locations:
            distance_to_enemy_start = el.distance_to(self.enemy_start_locations[0])
            self.expand_dis_dir[distance_to_enemy_start] = el

        self.ordered_exp_distances = sorted(k for k in self.expand_dis_dir)

        existing_ids = [unit.tag for unit in self.units]
        to_be_removed = []
        for noted_scout in self.scouts_and_spots:
            if noted_scout not in existing_ids:
                to_be_removed.append(noted_scout)

        for scout in to_be_removed:
            del self.scouts_and_spots[scout]

        if len(self.structures(UnitTypeId.ROBOTICSFACILITY).ready) == 0:
            unit_type = UnitTypeId.PROBE
            unit_limit = 1
        else:
            unit_type = UnitTypeId.OBSERVER
            unit_limit = 3

        assign_scout = True

        if unit_type == UnitTypeId.PROBE:
            for unit in self.units(UnitTypeId.PROBE):
                if unit.tag in self.scouts_and_spots:
                    assign_scout = False

        if assign_scout:
            if len(self.units(unit_type).idle) > 0:
                for obs in self.units(unit_type).idle[:unit_limit]:
                    if obs.tag not in self.scouts_and_spots:
                        for dist in self.ordered_exp_distances:
                            try:
                                location = next(value for key, value in self.expand_dis_dir.items() if key == dist)
                                active_locations = [self.scouts_and_spots[k] for k in self.scouts_and_spots]

                                if location not in active_locations:
                                    if unit_type == UnitTypeId.PROBE:
                                        for unit in self.units(UnitTypeId.PROBE):
                                            if unit.tag in self.scouts_and_spots:
                                                continue
                                    await self.do(obs.move(location))
                                    self.scouts_and_spots[obs.tag] = location
                                    break
                            except Exception as e:
                                pass

        for obs in self.units(unit_type):
            if obs.tag in self.scouts_and_spots:
                if obs in [probe for probe in self.units(UnitTypeId.PROBE)]:
                    obs.move(self.random_location(self.scouts_and_spots[obs.tag]))

    async def vision(self):
        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

        draw_dic = {
            UnitTypeId.NEXUS: [5, (0, 255, 0)],
            UnitTypeId.PYLON: [2, (20, 235, 0)],
            UnitTypeId.PROBE: [1, (55, 200, 0)],
            UnitTypeId.ASSIMILATOR: [2, (55, 200, 0)],
            UnitTypeId.GATEWAY: [3, (200, 100, 0)],
            UnitTypeId.CYBERNETICSCORE: [3, (150, 150, 0)],
            UnitTypeId.STARGATE: [3, (255, 0, 0)],
            UnitTypeId.ROBOTICSFACILITY: [3, (215, 155, 0)],
            UnitTypeId.VOIDRAY: [2, (255, 100, 0)],
        }

        for unit_type in draw_dic:
            for unit in self.units(unit_type).ready or self.structures(unit_type).ready:
                pos = unit.position
                cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dic[unit_type][0], draw_dic[unit_type][1], -1)

        main_base_names = ['nexus', 'commandcenter', 'orbitalcommand', 'planetaryfortress', 'hatchery']
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

        for vr in self.units(UnitTypeId.VOIDRAY).ready:
            pos = vr.position
            cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (255, 100, 0), -1)

        line_max = 50
        mineral_ratio = self.minerals / 1500
        if mineral_ratio > 1.0:
            mineral_ratio = 1.0

        vespene_ratio = self.vespene / 1500
        if vespene_ratio > 1.0:
            vespene_ratio = 1.0

        population_ratio = self.supply_left / self.supply_cap
        if population_ratio > 1.0:
            population_ratio = 1.0

        plausible_supply = self.supply_cap / 200.0

        military_weight = len(self.units(UnitTypeId.VOIDRAY)) / (self.supply_cap - self.supply_left)
        if military_weight > 1.0:
            military_weight = 1.0

        cv2.line(game_data, (0, 19), (int(line_max * military_weight), 19), (250, 250, 200), 3)
        cv2.line(game_data, (0, 13), (int(line_max * plausible_supply), 13), (220, 200, 200), 3)
        cv2.line(game_data, (0, 11), (int(line_max * population_ratio), 11), (150, 150, 150), 3)
        cv2.line(game_data, (0, 7), (int(line_max * vespene_ratio), 7), (210, 200, 0), 3)
        cv2.line(game_data, (0, 3), (int(line_max * mineral_ratio), 3), (0, 255, 25), 3)

        self.flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(self.flipped, dsize=None, fx=3, fy=3)

        if not HEADLESS:
            cv2.imshow(str(self.title), resized)
            cv2.waitKey(1)

    def find_enemy(self, state):
        if len(self.enemy_units) > 0:
            return random.choice(self.enemy_units)
        elif len(self.enemy_structures) > 0:
            return random.choice(self.enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def build_scout(self):
        if len(self.units(UnitTypeId.OBSERVER)) < math.floor(self.GameTime / 3):
            for rf in self.structures(UnitTypeId.ROBOTICSFACILITY).ready.idle:
                print(len(self.units(UnitTypeId.OBSERVER)), self.GameTime / 3)
                if self.can_afford(UnitTypeId.OBSERVER) and self.supply_left > 0:
                    rf.train(UnitTypeId.OBSERVER)

    async def build_zealot(self):
        gateways = self.structures(UnitTypeId.GATEWAY).ready
        if gateways.exists:
            if self.unit(UnitTypeId.ZEALOT).can_afford:
                await self.do(random.choice(gateways).train(UnitTypeId.ZEALOT))

    async def build_gateway(self):
        pylon1 = self.structures(UnitTypeId.PYLON).ready.random
        if self.structures(UnitTypeId.GATEWAY).can_afford and not self.structures(UnitTypeId.GATEWAY).already_pending:
            await self.build(UnitTypeId.GATEWAY, near=pylon1)

    async def build_stalker(self):
        pylon1 = self.structures(UnitTypeId.PYLON).ready.random
        gateways = self.structures(UnitTypeId.GATEWAY).ready
        cybernetics_core = self.structures(UnitTypeId.CYBERNETICSCORE).ready

        if gateways.exists and cybernetics_core.exists:
            if self.units(UnitTypeId.STALKER).can_afford:
                await self.do(random.choice(gateways).train(UnitTypeId.STALKER))

        if not cybernetics_core.exists:
            if self.structures(UnitTypeId.GATEWAY).ready.exists:
                if self.structures(UnitTypeId.CYBERNETICSCORE).can_afford and not self.structures(
                        UnitTypeId.CYBERNETICSCORE).already_pending:
                    await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon1)

    async def build_voidray(self):
        stargates = self.structures(UnitTypeId.STARGATE).ready
        if stargates.exists:
            if self.units(UnitTypeId.VOIDRAY).can_afford:
                await self.do(random.choice(stargates).train(UnitTypeId.VOIDRAY))

    async def build_workers(self):
        CurrentAmountHalls = self.townhalls.ready.amount
        CurrentProbes = self.workers.amount
        MaxProbes = (22 * CurrentAmountHalls) - 2
        nexuses = self.structures(UnitTypeId.NEXUS).ready
        if nexuses.exists:
            if not self.already_pending(UnitTypeId.PROBE) and (CurrentProbes < MaxProbes):
                if self.units(UnitTypeId.PROBE).can_afford:
                    await self.do(random.choice(choices).train(UnitTypeId.PROBE))

    async def build_assimilators(self):
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

    async def build_stargate(self):
        if self.structures(UnitTypeId.PYLON).ready.exists:
            pylon1 = self.structures(UnitTypeId.PYLON).ready.random
            if self.structures(UnitTypeId.CYBERNETICSCORE).ready.exists:
                if self.structures(UnitTypeId.STARGATE).can_afford and not self.structures(
                        UnitTypeId.STARGATE).already_pending:
                    await self.build(UnitTypeId.STARGATE, near=pylon1)

    async def build_pylons(self):
        if self.supply_left < 3 and not self.already_pending(UnitTypeId.PYLON):
            nexuses = self.townhalls.ready
            if nexuses.exists:
                if self.can_afford(UnitTypeId.PYLON):
                    await self.build(UnitTypeId.PYLON, near=self.structures(UnitTypeId.NEXUS).first.position.towards(
                        self.game_info.map.center, 5))

    async def defend_nexus(self):
        if len(self.known_enemy_units) > 0:
            target = self.attack_known_enemy_units.closest_to(random.choice(self.units(UnitTypeId.NEXUS)))
            for u in self.units(UnitTypeId.VOIDRAY).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.STALKER).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.ZEALOT).idle:
                await self.do(u.attack(target))

    async def attack_known_enemy_unit(self):
        if len(self.known_enemy_units) > 0:
            target = self.attack_known_enemy_units.closest_to(random.choice(self.units(UnitTypeId.NEXUS)))
        for u in self.units(UnitTypeId.VOIDRAY).idle:
            await self.do(u.attack(target))
        for u in self.units(UnitTypeId.STALKER).idle:
            await self.do(u.attack(target))
        for u in self.units(UnitTypeId.ZEALOT).idle:
            await self.do(u.attack(target))

    async def attack_known_enemy_structure(self):
        if len(self.attack_known_enemy_structures) > 0:
            target = random.choice(self.attack_known_enemy_structures)
        for u in self.units(UnitTypeId.VOIDRAY).idle:
            await self.do(u.attack(target))
        for u in self.units(UnitTypeId.STALKER).idle:
            await self.do(u.attack(target))
        for u in self.units(UnitTypeId.ZEALOT).idle:
            await self.do(u.attack(target))

    async def expand(self):
        try:
            if self.structures(UnitTypeId.NEXUS).can_afford:
                await self.expand_now()
        except Exception as e:
            print(str(e))

    async def do_nothing(self):
        wait = random.randrange(7, 100) / 100
        self.do_something_after = self.GameTime + wait

    async def defend_nexus(self):
        if len(self.enemy_units) > 0:
            target = self.enemy_units.closest_to(random.choice(self.structures(UnitTypeId.NEXUS)))
            for u in self.units(UnitTypeId.VOIDRAY).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.STALKER).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.ZEALOT).idle:
                await self.do(u.attack(target))

    async def attack_known_enemy_structure(self):
        if len(self.enemy_structures) > 0:
            target = random.choice(self.enemy_structures)
            for u in self.units(UnitTypeId.VOIDRAY).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.STALKER).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.ZEALOT).idle:
                await self.do(u.attack(target))

    async def attack_known_enemy_unit(self):
        if len(self.enemy_units) > 0:
            target = self.enemy_units.closest_to(random.choice(self.structures(UnitTypeId.NEXUS)))
            for u in self.units(UnitTypeId.VOIDRAY).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.STALKER).idle:
                await self.do(u.attack(target))
            for u in self.units(UnitTypeId.ZEALOT).idle:
                await self.do(u.attack(target))

    async def distribute_workers(self):
        pass

    async def do_something(self):
        if self.GameTime > self.do_something_after:
            if self.use_model:
                prediction = self.model.predict([self.flipped.reshape([-1, 176, 200, 3])])
                choice = np.argmax(prediction[0])
            else:
                choice = random.randrange(0, 14)
            try:
                await self.choices[choice]()
            except Exception as e:
                print(str(e))
            y = np.zeros(14)
            y[choice] = 1
            self.train_data.append([y, self.flipped])

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
        Bot(sc2.Race.Protoss, AleeksBot(use_model=True)),
        Computer(sc2.Race.Terran, sc2.Difficulty.Medium)
    ],
    realtime=False
)
