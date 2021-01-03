from model import *
import random


class MyStrategy:

    def __init__(self):
        self.builder_count = 1
        self.unit_count = 3
        self.current_population = 3
        self.max_population = 15
        self.busy = {}
        self.repairing = {}
        self.entity_positions = {}
        self.making_house = 0
        self.game_stage = 0
        self.my_territory_border_x = 0
        self.my_territory_border_y = 0
        self.enemy_base_positions = [None]*5
        self.my_base_position = None
        self.map_center = None
        self.players_alive = [1]*5
        self.number_of_enemy_players = 0
        self.other_player_ids = []
        self.remaining_enemies = []
        #self.building_cap = 


    # Gathering resources, buys units separately for each type and sends them to the opposite map corner with auto attack
    def get_action(self, player_view, debug_interface):

        result = Action({}) # Action: new actions for entities. Map<int32, EntityAction>. If entity does not get a new action, it continues to do previously set action

        my_id = player_view.my_id

        # Decremement making_house
        if self.making_house != 0:
            self.making_house -= 1

        # AT THE VERY BEGINNING OF THE GAME: Get position of the enemy bases and my base. Initialize reparing
        if player_view.current_tick == 0:
            for entity in player_view.entities:
                if entity.player_id not in self.other_player_ids and entity.entity_type != EntityType.RESOURCE and entity.player_id != my_id:
                    self.other_player_ids.append(entity.player_id)
                self.busy[entity.id] = 0

                if (entity.entity_type == EntityType.TURRET and entity.player_id != my_id):
                    self.enemy_base_positions[entity.player_id] = entity.position

                elif (entity.entity_type == EntityType.TURRET and entity.player_id == my_id):
                    self.my_base_position = entity.position

                if (entity.player_id == player_view.my_id and self._is_building(entity, player_view)):
                    self.repairing[entity.id] = 0

            self.number_of_enemy_players = len(self.other_player_ids)

            self.map_center = Vec2Int(player_view.map_size / 2, player_view.map_size / 2)

        # EVERY ROUND, BEFORE ASSIGNING ACTIONS: Get the current populations and positions of units and boundary of my occupied territory
        self.builder_count = 0
        self.current_population = 0
        self.max_population = 0
        self.unit_count = 0
        self.remaining_enemies = []
        for i in range(len(self.players_alive)): # Assume the other players are dead, correct if they aren't
            self.players_alive[i] = 0

        for entity in player_view.entities:
            self.entity_positions[entity.id] = Vec2Int(entity.position.x, entity.position.y)
            
            if entity.player_id != my_id:
                if (entity.entity_type != EntityType.RESOURCE):
                    for i in self.other_player_ids:
                        if (entity.position.x > self.enemy_base_positions[i].x-10 and entity.position.x < self.enemy_base_positions[i].x+10 and entity.position.y > self.enemy_base_positions[i].y-10 and entity.position.y < self.enemy_base_positions[i].y+10):
                            self.players_alive[i] = 1

                    self.remaining_enemies.append(entity)
                continue

            if (entity.entity_type != EntityType.MELEE_UNIT and entity.entity_type != EntityType.RANGED_UNIT):
                if entity.position.x > self.my_territory_border_x:
                    self.my_territory_border_x = entity.position.x
                if entity.position.y > self.my_territory_border_y:
                    self.my_territory_border_y = entity.position.y

            if entity.entity_type == EntityType.BUILDER_UNIT:
                self.builder_count += 1

            if (entity.entity_type == EntityType.BUILDER_UNIT or entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT):
                self.unit_count += 1

            if player_view.entity_properties[entity.entity_type].population_use:
                self.current_population = self.current_population + player_view.entity_properties[entity.entity_type].population_use

            if player_view.entity_properties[entity.entity_type].population_provide and entity.health == player_view.entity_properties[entity.entity_type].max_health:
                self.max_population = self.max_population + player_view.entity_properties[entity.entity_type].population_provide

        # Set the game stage: EARLY, MID, LATE
        if (self.builder_count <=12):
            self.game_stage = 0
        elif (self.builder_count > 12 and self.unit_count < 60):
            self.game_stage = 1
        elif (self.builder_count > 12 and self.unit_count >= 60):
            self.game_stage = 2




        # EARLY GAME: Make builders
        if (self.game_stage == 0):

            # Loop through the entities
            for entity in player_view.entities:

                # Ignore entities that aren't mine
                if (entity.player_id != my_id):
                    continue

                # If the entity does not have an entry in busy (it is newly created), set it to zero
                if entity.id not in self.busy.keys():
                    self.busy[entity.id] = 0

                move_action, build_action, attack_action, repair_action = None, None, None, None

                # Get properties of the current entity
                properties = player_view.entity_properties[entity.entity_type]
                    
                # BUILDER UNITS: Build and repair house if necessary, otherwise mine nearby resources
                if entity.entity_type == EntityType.BUILDER_UNIT:

                    if self.busy[entity.id] == 0:

                        # Check if there are any buildings that are not at max health and are not being repaired already
                        buildings_to_repair = self._buildings_to_repair(player_view)
                        
                        if (self._make_house(player_view, entity)):
                            build_position = Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1)
                            build_action = BuildAction(EntityType.HOUSE, build_position)
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                            self.making_house = 5
                            self.busy[entity.id] = 5
                        
                        # Check if there are any buildings that are not at max health and are right next to the entity
                        # If the entity has just built something, it should repair it right after building it, since it will be nearby
                        elif self._nearby_building(entity, buildings_to_repair) and self.busy[entity.id] == 0:
                            building_to_repair = self._nearby_building(entity, buildings_to_repair)
                            repair_action = RepairAction(building_to_repair.id)
                            self.busy[entity.id] = 45
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                        # Otherwise, tell the builder to move to the opposite side of the map, but with autoattack (essentially tells them to mine nearby resources)
                        else:
                            move_action = MoveAction(Vec2Int(player_view.map_size - 1, player_view.map_size - 1),True,True)
                            attack_action = AttackAction(None, AutoAttack(properties.sight_range, [EntityType.RESOURCE]))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                    else:
                        self.busy[entity.id] -= 1

                # ATTACKING UNITS: Move to edge of base and patrol
                elif (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT):
                    
                    if self.busy[entity.id] == 0:
                        move_position = random.choice([Vec2Int(player_view.map_size - 60, player_view.map_size - 60), Vec2Int(player_view.map_size - 70, player_view.map_size - 60), Vec2Int(player_view.map_size - 60, player_view.map_size - 70)])
                        move_action = MoveAction(move_position, True, True)
                        attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))
                        
                        nearby_enemies = self._enemies_nearby(player_view)
                        if nearby_enemies:
                            enemy_to_attack = random.choice(nearby_enemies)
                            move_action = MoveAction(Vec2Int(enemy_to_attack.position.x, enemy_to_attack.position.y), True, True)
                            attack_action = AttackAction(enemy_to_attack.id, AutoAttack(properties.sight_range, []))
                        
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)
                        self.busy[entity.id] = 60
                    
                    else:
                        self.busy[entity.id] -= 1

                # BUILDER BASE: Make a unit every possible chance
                elif entity.entity_type == EntityType.BUILDER_BASE:
                    self._build_unit(player_view, result, entity, EntityType.BUILDER_UNIT)

                # MELEE and RANGED BASE: Make a unit every 30 ticks
                elif (entity.entity_type == EntityType.RANGED_BASE):
                    self._build_unit(player_view, result, entity, EntityType.RANGED_UNIT, 20)

                elif (entity.entity_type == EntityType.MELEE_BASE):
                    self._build_unit(player_view, result, entity, EntityType.MELEE_UNIT, 20)    
            
                # TURRETS: attack nearby enemies
                elif (entity.entity_type == EntityType.TURRET):
                    attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))
                    result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

            return result

        
        # MID GAME: Focus on building up army. 
        elif (self.game_stage == 1):

            # Loop through the entities
            for entity in player_view.entities:

                # Ignore entities that aren't mine
                if (entity.player_id != my_id):
                    continue

                # If the entity does not have an entry in busy (it is newly created), set it to zero
                if entity.id not in self.busy.keys():
                    self.busy[entity.id] = 0

                move_action, build_action, attack_action, repair_action = None, None, None, None

                # Get properties of the current entity
                properties = player_view.entity_properties[entity.entity_type]
                    
                # BUILDER UNITS: Build and repair house if necessary, otherwise mine nearby resources
                if entity.entity_type == EntityType.BUILDER_UNIT:

                    if self.busy[entity.id] == 0:

                        # Check if there are any buildings that are not at max health and are not being repaired already
                        buildings_to_repair = self._buildings_to_repair(player_view)

                        if (self._make_house(player_view, entity)):
                            build_position = Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1)
                            build_action = BuildAction(EntityType.HOUSE, build_position)
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                            self.making_house = 5
                            self.busy[entity.id] = 5
                        
                        # Check if there are any buildings that are not at max health and are right next to the entity
                        # If the entity has just built something, it should repair it right after building it, since it will be nearby
                        elif self._nearby_building(entity, buildings_to_repair) and self.busy[entity.id] == 0:
                            building_to_repair = self._nearby_building(entity, buildings_to_repair)
                            repair_action = RepairAction(building_to_repair.id)
                            self.busy[entity.id] = 45
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                        # Otherwise, tell the builder to move to the opposite side of the map, but with autoattack (essentially tells them to mine nearby resources)
                        else:
                            move_action = MoveAction(Vec2Int(player_view.map_size - 1, player_view.map_size - 1),True,True)
                            attack_action = AttackAction(None, AutoAttack(properties.sight_range, [EntityType.RESOURCE]))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                    else:
                        self.busy[entity.id] -= 1

                # ATTACKING UNITS: Move to edge of base and patrol
                elif (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT):
                    
                    if self.busy[entity.id] == 0:
                        move_position = random.choice([Vec2Int(self.my_territory_border_x+2, self.my_territory_border_y+2), Vec2Int(self.my_territory_border_x//2, self.my_territory_border_y+2), Vec2Int(self.my_territory_border_x+2, self.my_territory_border_y//2)])
                        move_action = MoveAction(move_position, True, False)
                        attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))
                        
                        nearby_enemies = self._enemies_nearby(player_view)
                        if nearby_enemies:
                            enemy_to_attack = random.choice(nearby_enemies)
                            move_action = MoveAction(Vec2Int(enemy_to_attack.position.x, enemy_to_attack.position.y), True, True)
                            attack_action = AttackAction(enemy_to_attack.id, AutoAttack(properties.sight_range, []))
                        
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)
                        self.busy[entity.id] = 40
                    
                    else:
                        self.busy[entity.id] -= 1

                # BUILDER BASE: Make a unit every 10 ticks
                elif entity.entity_type == EntityType.BUILDER_BASE:
                    self._build_unit(player_view, result, entity, EntityType.BUILDER_UNIT, 10)

                # MELEE and RANGED BASES: Make units every 5 ticks
                elif (entity.entity_type == EntityType.RANGED_BASE):
                    self._build_unit(player_view, result, entity, EntityType.RANGED_UNIT, 5)

                elif (entity.entity_type == EntityType.MELEE_BASE):
                    self._build_unit(player_view, result, entity, EntityType.MELEE_UNIT, 5)        

                # TURRETS: attack nearby enemies
                elif (entity.entity_type == EntityType.TURRET):
                    attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))
                    result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

            return result


        # LATE GAME: attac
        elif (self.game_stage == 2):

            # Loop through the entities
            for entity in player_view.entities:

                # Ignore entities that aren't mine
                if (entity.player_id != my_id):
                    continue

                # If the entity does not have an entry in busy (it is newly created), set it to zero
                if entity.id not in self.busy.keys():
                    self.busy[entity.id] = 0

                move_action, build_action, attack_action, repair_action = None, None, None, None

                # Get properties of the current entity
                properties = player_view.entity_properties[entity.entity_type]
                    
                # BUILDER UNITS: Build and repair house if necessary, otherwise mine nearby resources
                if entity.entity_type == EntityType.BUILDER_UNIT:

                    if self.busy[entity.id] == 0:

                        # Check if there are any buildings that are not at max health and are not being repaired already
                        buildings_to_repair = self._buildings_to_repair(player_view)

                        build_position = Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1)
                        
                        make_turret = self._make_turret(player_view, entity)
                        make_house = self._make_house(player_view, entity)
                        if (make_house or make_turret):
                            if (entity.position.x < 35 and entity.position.y < 35):
                                if (make_house):
                                    build_action = BuildAction(EntityType.HOUSE, build_position)
                            else:
                                if (make_turret):
                                    build_action = BuildAction(EntityType.TURRET, build_position)

                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                            self.making_house = 4
                            self.busy[entity.id] = 10
                        
                        # Check if there are any buildings that are not at max health and are right next to the entity
                        # If the entity has just built something, it should repair it right after building it, since it will be nearby
                        elif self._nearby_building(entity, buildings_to_repair) and self.busy[entity.id] == 0:
                            building_to_repair = self._nearby_building(entity, buildings_to_repair)
                            repair_action = RepairAction(building_to_repair.id)
                            self.busy[entity.id] = 45
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                        # Otherwise, tell the builder to move to the opposite side of the map, but with autoattack (essentially tells them to mine nearby resources)
                        else:
                            move_action = MoveAction(Vec2Int(player_view.map_size - 1, player_view.map_size - 1),True,True)
                            attack_action = AttackAction(None, AutoAttack(properties.sight_range, [EntityType.RESOURCE]))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                    else:
                        self.busy[entity.id] -= 1

                # ATTACKING UNITS: Attack remaining enemies
                elif (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT):
                    
                    if self.busy[entity.id] == 0:
                        attacking_positions = []
                        for i in self.other_player_ids:
                            if (self.players_alive[i]):
                                attacking_positions.append(self.enemy_base_positions[i])

                        if attacking_positions:
                            move_position = random.choice(attacking_positions)
                            move_action = MoveAction(move_position, True, False)
                            attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))

                        elif self.remaining_enemies:
                            enemy_to_attack = random.choice(self.remaining_enemies)
                            move_action = MoveAction(Vec2Int(enemy_to_attack.position.x, enemy_to_attack.position.y), True, True)
                            attack_action = AttackAction(enemy_to_attack.id, AutoAttack(properties.sight_range, []))

                        nearby_enemies = self._enemies_nearby(player_view)
                        if nearby_enemies:
                            enemy_to_attack = random.choice(nearby_enemies)
                            move_action = MoveAction(Vec2Int(enemy_to_attack.position.x, enemy_to_attack.position.y), True, True)
                            attack_action = AttackAction(enemy_to_attack.id, AutoAttack(properties.sight_range, []))
                        
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)
                        self.busy[entity.id] = 80
                    
                    else:
                        self.busy[entity.id] -= 1

                # BUILDER BASE: Make a unit every 10 ticks
                elif entity.entity_type == EntityType.BUILDER_BASE:
                    self._build_unit(player_view, result, entity, EntityType.BUILDER_UNIT, 10)

                # MELEE and RANGED BASE: Build a unit every 1/2 ticks
                elif (entity.entity_type == EntityType.RANGED_BASE):
                    self._build_unit(player_view, result, entity, EntityType.RANGED_UNIT, 1)

                elif (entity.entity_type == EntityType.MELEE_BASE):
                    self._build_unit(player_view, result, entity, EntityType.MELEE_UNIT, 2)

                # TURRETS: attack nearby enemies
                elif (entity.entity_type == EntityType.TURRET):
                    attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))
                    result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

            return result

    def _make_turret(self, player_view, builder):
        if not((self.making_house == 0) and (player_view.players[player_view.my_id-1].resource > 50)):
            return False
        for entity in player_view.entities:
            if (entity.position.x > builder.position.x and entity.position.x < builder.position.x+3 and entity.position.y >= builder.position.y and entity.position.y < builder.position.y+2):
                return False
        return True

    def _make_house(self, player_view, builder):
        if not((self.making_house == 0) and (self.current_population > (self.max_population-10)) and (player_view.players[player_view.my_id-1].resource > 50)):
            return False
        for entity in player_view.entities:
            if (entity.position.x > builder.position.x and entity.position.x < builder.position.x+4 and entity.position.y >= builder.position.y and entity.position.y < builder.position.y+3):
                return False
        return True

    def _build_unit(self, player_view, result, base, unit_type, freq=1):
        cost_to_build = player_view.entity_properties[unit_type].initial_cost
        move_action, build_action, attack_action, repair_action = None, None, None, None
        properties = player_view.entity_properties[base.entity_type]
        if (unit_type == EntityType.BUILDER_UNIT and (self.builder_count > (self.max_population//2)) and self.game_stage == 2):
            pass
        elif (player_view.current_tick % freq == 0 and player_view.players[player_view.my_id-1].resource > cost_to_build and self.current_population + 1 <= self.max_population):
            build_action = BuildAction(unit_type, Vec2Int(base.position.x + properties.size, base.position.y + properties.size - 1))
            result.entity_actions[base.id] = EntityAction(move_action, build_action, attack_action, repair_action)

    def _enemies_near_initial_base(self, player_view):

        enemies = []
        for entity in player_view.entities:

            # Ignore my units and resources
            if ((entity.player_id == player_view.my_id) or (entity.entity_type == EntityType.RESOURCE)):
                continue
            
            # Check if they are near my inital base position
            if ((entity.position.x < (player_view.map_size - 50)) and (entity.position.y < (player_view.map_size - 50))):
                enemies.append(entity)

        return enemies

    def _enemies_nearby(self, player_view):

        enemies = []
        for entity in player_view.entities:

            # Ignore my units and resources
            if ((entity.player_id == player_view.my_id) or (entity.entity_type == EntityType.RESOURCE)):
                continue
            
            # Check if they are near any of my units
            if ((entity.position.x < self.my_territory_border_x+7) and (entity.position.y < self.my_territory_border_y+7)):
                enemies.append(entity)

        return enemies

    def _nearby_building(self, builder, buildings):
        for building in buildings:
            if ((abs(building.position.x - builder.position.x) < 2) and (abs(building.position.y - builder.position.y) < 2)):
                return building
        return None

    def _buildings_to_repair(self, player_view):

        buildings_to_repair = []
        for entity in player_view.entities:
            if (entity.player_id != player_view.my_id):
                continue

            if (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT or entity.entity_type == EntityType.BUILDER_UNIT):
                continue

            if entity.id not in self.repairing.keys():
                self.repairing[entity.id] = 0

            if (self._is_building(entity, player_view) and entity.health == player_view.entity_properties[entity.entity_type].max_health):
                self.repairing[entity.id] = 0

            elif (entity.health != player_view.entity_properties[entity.entity_type].max_health):
            #if ((entity.health != player_view.entity_properties[entity.entity_type].max_health)):
                buildings_to_repair.append(entity)

        return buildings_to_repair

    def _is_building(self, entity, player_view):
        if (entity.entity_type == EntityType.MELEE_BASE or entity.entity_type == EntityType.RANGED_BASE or entity.entity_type == EntityType.WALL or entity.entity_type == EntityType.BUILDER_BASE or entity.entity_type == EntityType.TURRET or entity.entity_type == EntityType.HOUSE):
            return True
        else:
            return False

    def debug_update(self, player_view, debug_interface):
        #vertex = ColoredVertex(Vec2Float(15, 15), 0, Color(225, 0, 0, 1))

        #debug_interface.send(DebugCommand.Add(DebugData.PlacedText(ColoredVertex(None, 3, Color(5, 5, 5, 1)), "f", 0.5, 13)))
        #debug_interface.send(DebugCommand.Add(DebugData.Log("hello")))
        
        debug_interface.send(DebugCommand.Clear())
        debug_interface.get_state()
