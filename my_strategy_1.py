from model import *
import random


class MyStrategy1:

    def __init__(self):
        self.builder_count = 1
        self.unit_count = 3
        self.current_population = 3
        self.max_population = 15
        self.enemy_base_positions = []
        self.my_base_position = None
        self.map_center = None
        self.busy = {}
    
    # Gathering resources, buys units separately for each type and sends them to the opposite map corner with auto attack
    def get_action(self, player_view, debug_interface):

        result = Action({}) # Action: new actions for entities. Map<int32, EntityAction>. If entity does not get a new action, it continues to do previously set action

        my_id = player_view.my_id # Gets my player id
        making_house = False

        # Get positions of the initial buildings (so we know where not to build / where to build the houses)
        # Get positions of the other three bases
        if player_view.current_tick == 0:

            for entity in player_view.entities:

                self.busy[entity.id] = 0

                if (entity.entity_type == EntityType.TURRET and entity.player_id != my_id):
                    self.enemy_base_positions.append(entity.position)

                elif (entity.entity_type == EntityType.TURRET and entity.player_id == my_id):
                    self.my_base_position = entity.position

            self.map_center = Vec2Int(player_view.map_size / 2, player_view.map_size / 2)

            print(self.map_center)
            print(self.enemy_base_positions)
            print(self.my_base_position)
            print(self.busy)


        # Get the current unit counts and population (unable to keep track just by incrementing after building units)
        self.builder_count = 0
        self.current_population = 0
        self.max_population = 0
        for entity in player_view.entities:
            if entity.player_id != my_id:
                continue

            if entity.entity_type == EntityType.BUILDER_UNIT:
                self.builder_count += 1

            if player_view.entity_properties[entity.entity_type].population_use:
                self.current_population = self.current_population + player_view.entity_properties[entity.entity_type].population_use

            if player_view.entity_properties[entity.entity_type].population_provide:
                self.max_population = self.max_population + player_view.entity_properties[entity.entity_type].population_provide


        # When we have less than 10 builders (early game):
        # if (builder_count <= 10):
        if True:

            # Loop through the entities
            for entity in player_view.entities:

                if entity.player_id != my_id:
                    continue

                if entity.id not in self.busy.keys():
                    self.busy[entity.id] = 0


                move_action, build_action, attack_action, repair_action = None, None, None, None

                # Get properties of the current entity
                properties = player_view.entity_properties[entity.entity_type]
                    
                # If we have a population that is close to the maximum, assign a builder to make a house
                # If it’s a builder, find nearest resource and mine
                if entity.entity_type == EntityType.BUILDER_UNIT:

                    if self.busy[entity.id] == 0:
                        if ((not making_house) and (self.current_population > (self.max_population-3))):
                    
                            print("just get a house 4Head")

                            '''
                            build_position = ?
                            build_action = BuildAction(EntityType.HOUSE, )'''

                            making_house = True
                            self.busy[entity.id] = 10
                        else:
                            # Tell the builder to move to the opposite side of the map, but with autoattack (essentially tells them to mine nearby resources)
                            move_action = MoveAction(Vec2Int(player_view.map_size - 1, player_view.map_size - 1),True,True)
                            attack_action = AttackAction(None, AutoAttack(properties.sight_range, [EntityType.RESOURCE]))
                            result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)

                    else:
                        self.busy[entity.id] -= 1


                # If it's a builderBase, construct a builder every possible chance
                elif entity.entity_type == EntityType.BUILDER_BASE:

                    # Check if we can make a builder
                    if ((self.current_population + 1 <= self.max_population)):
                        
                        # Tell the builderbase to make a builder
                        build_action = BuildAction(EntityType.BUILDER_UNIT, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)
                        
                # If it is a non-builder unit, then move to the edge of the base and autoattack []
                elif (entity.entity_type == EntityType.MELEE_UNIT or entity.entity_type == EntityType.RANGED_UNIT):
                    
                    if self.busy[entity.id] == 0:
                        move_position = random.choice([Vec2Int(player_view.map_size - 60, player_view.map_size - 60), Vec2Int(player_view.map_size - 70, player_view.map_size - 60), Vec2Int(player_view.map_size - 60, player_view.map_size - 70)])
                        move_action = MoveAction(move_position, True, True)
                        attack_action = AttackAction(None, AutoAttack(properties.sight_range, []))

                        
                        nearby_enemies = self._enemies_near_initial_base(player_view, debug_interface)
                        if nearby_enemies:
                            print("nearby enemies")
                            # move_action = move_action = MoveAction(Vec2Int(nearby_enemies[0].position.x, nearby_enemies[0].position.y), True, True)
                            attack_action = AttackAction(nearby_enemies[0].id, AutoAttack(properties.sight_range, []))
                        
                        result.entity_actions[entity.id] = EntityAction(move_action, build_action, attack_action, repair_action)
                        self.busy[entity.id] = 20
                    
                    else:
                        self.busy[entity.id] -= 1



            return result


        # When we have more than 10 builders (post-early game), but before 50 units:
        elif (self.builder_count > 10 and self.unit_count < 50):
            # Check whether we need to repair any buildings
            # Loop through the entities
                # If I don't own the entity, then check if it is near my base. If so, attack it
                # If we have a population that is close to the maximum, assign a builder to make a house
                # If it’s a builder, find nearest resource and mine
                # If it's a builderBase, make a builder every 5 ticks
                # If it's a meleeBase or rangedBased, make a melee unit every 3 ticks
                # If it is a non-builder unit, then move to the edge of the base and autoattack []
                # Send occasional troops?
            print("hi")

        elif (self.unit_count >= 50):
            # When we had more than 50 units:
            # Check whether we need to repair any buildings
            # Loop through the entities 
                # If I don't own the entity, check if it is near my base. If so, attack it
                # If we have a population that is close to the maximum, assign a builder to make a house
                # If it’s a builder, find nearest resource and mine
                # If it's a builderBase, make a builder every 5 ticks
                # If it's a meleeBase or rangedBased, make a melee unit every 3 ticks
            # Check how many buildings each player owns, and send troops in proportion to those numbers
            print("hi2")



        return result


    def _enemies_near_initial_base(self, player_view, debug_interface):

        enemies = []
        for entity in player_view.entities:

            if (entity.player_id == player_view.my_id):
                continue

            if (entity.position.x < player_view.map_size - 55 and entity.position.y < player_view.map_size - 55):
                enemies.append(entity)

        return enemies

    def _need_to_repair_buildings():

        return 0

    def debug_update(self, player_view, debug_interface):
        #vertex = ColoredVertex(Vec2Float(15, 15), 0, Color(225, 0, 0, 1))

        #debug_interface.send(DebugCommand.Add(DebugData.PlacedText(ColoredVertex(None, 3, Color(5, 5, 5, 1)), "f", 0.5, 13)))
        #debug_interface.send(DebugCommand.Add(DebugData.Log("hello")))
        
        debug_interface.send(DebugCommand.Clear())
        debug_interface.get_state()
