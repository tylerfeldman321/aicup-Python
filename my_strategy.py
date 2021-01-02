from model import *
import random


class MyStrategy:

    def __init__(self):
        self.builder_count = 1
        self.unit_count = 3
        self.current_population = 3
        self.max_population = 15
        self.enemy_base_positions = []
        self.my_base_position = None
        self.map_center = None
        self.busy = {}
        self.repairing = {}
        self.entity_positions = {}
        self.making_house = 0
        self.my_territory_border_x = 0
        self.my_territory_border_y = 0
    
    # Gathering resources, buys units separately for each type and sends them to the opposite map corner with auto attack
    def get_action(self, player_view, debug_interface):

        result = Action({}) # Action: new actions for entities. Map<int32, EntityAction>. If entity does not get a new action, it continues to do previously set action

        my_id = player_view.my_id
        print(player_view.players[my_id-1].resource)
        # Decremement making_house
        if self.making_house != 0:
            self.making_house -= 1

        # AT THE VERY BEGINNING OF THE GAME: Get position of the enemy bases and my base. Initialize reparing
        if player_view.current_tick == 0:

            for entity in player_view.entities:

                self.busy[entity.id] = 0

                if (entity.entity_type == EntityType.TURRET and entity.player_id != my_id):
                    self.enemy_base_positions.append(entity.position)

                elif (entity.entity_type == EntityType.TURRET and entity.player_id == my_id):
                    self.my_base_position = entity.position

                if (entity.player_id == player_view.my_id and self._is_building(entity, player_view, debug_interface)):
                    self.repairing[entity.id] = 0
                

            self.map_center = Vec2Int(player_view.map_size / 2, player_view.map_size / 2)

            print(self.map_center)
            print(self.enemy_base_positions)
            print(self.my_base_position)

        # EVERY ROUND, BEFORE ASSIGNING ACTIONS: Get the current populations and positions of units and boundary of my occupied territory
        self.builder_count = 0
        self.current_population = 0
        self.max_population = 0
        for entity in player_view.entities:
            self.entity_positions[entity.id] = Vec2Int(entity.position.x, entity.position.y)

            if (entity.player_id == my_id and entity.entity_type != EntityType.MELEE_UNIT and entity.entity_type != EntityType.RANGED_UNIT):
                #print(entity.position.x, entity.position.y)
                if entity.position.x > self.my_territory_border_x:
                    self.my_territory_border_x = entity.position.x
                if entity.position.y > self.my_territory_border_y:
                    self.my_territory_border_y = entity.position.y

            if entity.player_id != my_id:
                continue

            if entity.entity_type == EntityType.BUILDER_UNIT:
                self.builder_count += 1

            if player_view.entity_properties[entity.entity_type].population_use:
                self.current_population = self.current_population + player_view.entity_properties[entity.entity_type].population_use

            if player_view.entity_properties[entity.entity_type].population_provide:
                self.max_population = self.max_population + player_view.entity_properties[entity.entity_type].population_provide

        #if (player_view.current_tick % 10 == 0):
        #    print(self.my_territory_border_x, self.my_territory_border_y)


        # EARLY GAME: Make builders
        if (self.builder_count <= 12):
        #if True:

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
                        buildings_to_repair = self._buildings_to_repair(player_view, debug_interface)

                        if ((self.making_house == 0) and (self.current_population > (self.max_population-10)) and (player_view.players[my_id-1].resource > 50)):
                    
                            print('attempting to build house')
                            build_position = Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1)
                            build_action = BuildAction(EntityType.HOUSE, build_position)
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                            self.making_house = 5
                            self.busy[entity.id] = 10
                        
                        # Check if there are any buildings that are not at max health and are right next to the entity
                        # If the entity has just built something, it should repair it right after building it, since it will be nearby
                        elif self._nearby_building(entity, buildings_to_repair) and self.busy[entity.id] == 0:
                            print('need to repair!')
                            building_to_repair = self._nearby_building(entity, buildings_to_repair)
                            repair_action = RepairAction(building_to_repair.id)
                            self.busy[entity.id] = 100
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                        # Otherwise, tell the builder to move to the opposite side of the map, but with autoattack (essentially tells them to mine nearby resources)
                        else:
                            move_action = MoveAction(Vec2Int(player_view.map_size - 1, player_view.map_size - 1),True,True)
                            attack_action = AttackAction(None, AutoAttack(properties.sight_range, [EntityType.RESOURCE]))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                    else:
                        self.busy[entity.id] -= 1


                # BUILDER BASE: Make a unit every possible chance
                elif entity.entity_type == EntityType.BUILDER_BASE:

                    # Check if we can make a builder
                    if ((self.current_population + 1 <= self.max_population)):
                        
                        # Tell the builderbase to make a builder
                        build_action = BuildAction(EntityType.BUILDER_UNIT, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)


                # ATTACKING UNITS: Move to edge of base and patrol
                elif (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT):
                    
                    if self.busy[entity.id] == 0:
                        move_position = random.choice([Vec2Int(player_view.map_size - 60, player_view.map_size - 60), Vec2Int(player_view.map_size - 70, player_view.map_size - 60), Vec2Int(player_view.map_size - 60, player_view.map_size - 70)])
                        #move_position = random.choice([Vec2Int(self.my_territory_border_x+2, self.my_territory_border_y+2), Vec2Int(self.my_territory_border_x//2, self.my_territory_border_y+2), Vec2Int(self.my_territory_border_x+2, self.my_territory_border_y//2)])
                        move_action = MoveAction(move_position, True, True)
                        attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))

                        
                        nearby_enemies = self._enemies_nearby(player_view, debug_interface)
                        if nearby_enemies:
                            print('nearby enemies!')
                            enemy_to_attack = random.choice(nearby_enemies)
                            attack_action = AttackAction(enemy_to_attack.id, AutoAttack(properties.sight_range, []))
                        
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)
                        self.busy[entity.id] = 40
                    
                    else:
                        self.busy[entity.id] -= 1

                # MELEE and RANGED BASE: Build a unit every 5 ticks
                elif (entity.entity_type == EntityType.RANGED_BASE):
                    # Do every 5 ticks
                    if (player_view.current_tick % 20 and player_view.players[my_id-1].resource > 30):
                        # Check if we can make a unit
                        if ((self.current_population + 1 <= self.max_population)):
                            # Tell the base to make a unit
                            build_action = BuildAction(EntityType.RANGED_UNIT, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                elif (entity.entity_type == EntityType.MELEE_BASE):
                    # Do every 5 ticks
                    if (player_view.current_tick % 20 and player_view.players[my_id-1].resource > 20):
                        # Check if we can make a unit
                        if ((self.current_population + 1 <= self.max_population)):
                            # Tell the base to make a unit
                            build_action = BuildAction(EntityType.MELEE_UNIT, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)     
            
            return result

        
        # MID GAME: Focus on building up army. 
        if (self.builder_count > 12):

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
                        buildings_to_repair = self._buildings_to_repair(player_view, debug_interface)

                        if ((self.making_house == 0) and (self.current_population > (self.max_population-10)) and (player_view.players[my_id-1].resource > 50)):
                    
                            print('attempting to build house')
                            build_position = Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1)
                            build_action = BuildAction(EntityType.HOUSE, build_position)
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                            self.making_house = 5
                            self.busy[entity.id] = 10
                        
                        # Check if there are any buildings that are not at max health and are right next to the entity
                        # If the entity has just built something, it should repair it right after building it, since it will be nearby
                        elif self._nearby_building(entity, buildings_to_repair) and self.busy[entity.id] == 0:
                            print('need to repair!')
                            building_to_repair = self._nearby_building(entity, buildings_to_repair)
                            repair_action = RepairAction(building_to_repair.id)
                            self.busy[entity.id] = 100
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                        # Otherwise, tell the builder to move to the opposite side of the map, but with autoattack (essentially tells them to mine nearby resources)
                        else:
                            move_action = MoveAction(Vec2Int(player_view.map_size - 1, player_view.map_size - 1),True,True)
                            attack_action = AttackAction(None, AutoAttack(properties.sight_range, [EntityType.RESOURCE]))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                    else:
                        self.busy[entity.id] -= 1


                # BUILDER BASE: Make a unit every 10 ticks
                elif entity.entity_type == EntityType.BUILDER_BASE:
                    if (player_view.current_tick % 10 == 0):
                        # Check if we can make a builder
                        if ((self.current_population + 1 <= self.max_population) and player_view.players[my_id-1].resource > 10):
                            
                            # Tell the builderbase to make a builder
                            build_action = BuildAction(EntityType.BUILDER_UNIT, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)


                # ATTACKING UNITS: Move to edge of base and patrol
                elif (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT):
                    
                    if self.busy[entity.id] == 0:
                        move_position = random.choice([Vec2Int(self.my_territory_border_x+2, self.my_territory_border_y+2), Vec2Int(self.my_territory_border_x//2, self.my_territory_border_y+2), Vec2Int(self.my_territory_border_x+2, self.my_territory_border_y//2)])
                        move_action = MoveAction(move_position, True, False)
                        attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))

                        
                        nearby_enemies = self._enemies_nearby(player_view, debug_interface)
                        if nearby_enemies:
                            print('nearby enemies!')
                            enemy_to_attack = random.choice(nearby_enemies)
                            attack_action = AttackAction(enemy_to_attack.id, AutoAttack(properties.sight_range, []))
                        
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)
                        self.busy[entity.id] = 40
                    
                    else:
                        self.busy[entity.id] -= 1

                # MELEE and RANGED BASE: Build a unit every 5 ticks
                elif (entity.entity_type == EntityType.RANGED_BASE):

                    # Do every 5 ticks
                    if (player_view.current_tick % 5 and player_view.players[my_id-1].resource > 30):
                        # Check if we can make a unit
                        if ((self.current_population + 1 <= self.max_population)):
                            # Tell the base to make a unit
                            build_action = BuildAction(EntityType.RANGED_UNIT, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                elif (entity.entity_type == EntityType.MELEE_BASE):

                    # Do every 5 ticks
                    if (player_view.current_tick % 5 and player_view.players[my_id-1].resource > 20):
                        # Check if we can make a unit
                        if ((self.current_population + 1 <= self.max_population)):
                            # Tell the base to make a unit
                            build_action = BuildAction(EntityType.MELEE_UNIT, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)            

            return result




        return result

    def _nearby_building(self, builder, buildings):
        for building in buildings:
            if ((abs(building.position.x - builder.position.x) < 2) and (abs(building.position.y - builder.position.y) < 2)):
                return building
        return None

    def _enemies_near_initial_base(self, player_view, debug_interface):

        enemies = []
        for entity in player_view.entities:

            # Ignore my units and resources
            if ((entity.player_id == player_view.my_id) or (entity.entity_type == EntityType.RESOURCE)):
                continue
            
            # Check if they are near my inital base position
            if ((entity.position.x < (player_view.map_size - 55)) and (entity.position.y < (player_view.map_size - 55))):
                enemies.append(entity)

        return enemies

    def _enemies_nearby(self, player_view, debug_interface):

        enemies = []
        for entity in player_view.entities:

            # Ignore my units and resources
            if ((entity.player_id == player_view.my_id) or (entity.entity_type == EntityType.RESOURCE)):
                continue
            
            # Check if they are near any of my units
            if ((entity.position.x < self.my_territory_border_x+7) and (entity.position.y < self.my_territory_border_y+7)):
                enemies.append(entity)

        return enemies


    def _buildings_to_repair(self, player_view, debug_interface):

        buildings_to_repair = []
        for entity in player_view.entities:
            if (entity.player_id != player_view.my_id):
                continue

            if (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT or entity.entity_type == EntityType.BUILDER_UNIT):
                continue

            if entity.id not in self.repairing.keys():
                self.repairing[entity.id] = 0

            #if (self._is_building(entity, player_view, debug_interface) and entity.health == player_view.entity_properties[entity.entity_type].max_health):
            if (self._is_building(entity, player_view, debug_interface) and entity.health == player_view.entity_properties[entity.entity_type].max_health):
                self.repairing[entity.id] = 0

            elif (entity.health != player_view.entity_properties[entity.entity_type].max_health):
            #if ((entity.health != player_view.entity_properties[entity.entity_type].max_health)):
                buildings_to_repair.append(entity)

        return buildings_to_repair

    def _is_building(self, entity, player_view, debug_interface):
        if (entity.entity_type == EntityType.MELEE_BASE or entity.entity_type == EntityType.RANGED_BASE or entity.entity_type == EntityType.WALL or entity.entity_type == EntityType.BUILDER_BASE or entity.entity_type == EntityType.TURRET or entity.entity_type == EntityType.HOUSE):
            return True
        else:
            return False

    def _find_place_for_house(self, player_view, debug_interface):
        #for ()
        #    for ()
        
        return Vec2Int(player_view.map_size-77, player_view.map_size-77)



    def debug_update(self, player_view, debug_interface):
        #vertex = ColoredVertex(Vec2Float(15, 15), 0, Color(225, 0, 0, 1))

        #debug_interface.send(DebugCommand.Add(DebugData.PlacedText(ColoredVertex(None, 3, Color(5, 5, 5, 1)), "f", 0.5, 13)))
        #debug_interface.send(DebugCommand.Add(DebugData.Log("hello")))
        
        debug_interface.send(DebugCommand.Clear())
        debug_interface.get_state()
