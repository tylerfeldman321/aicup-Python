from model import *


class ExampleStrategy:

    # Gathering resources, buys units separately for each type and sends them to the opposite map corner with auto attack
    def get_action(self, player_view, debug_interface):

        print(player_view.current_tick)

        result = Action({}) # Action: new actions for entities. Map<int32, EntityAction>. If entity does not get a new action, it continues to do previously set action

        my_id = player_view.my_id # Gets my player id

        # Loops through the entities in view
        for entity in player_view.entities:

            # Ignore entities that are not owned by me
            if entity.player_id != my_id:
                continue
            
            # Get the properties of the current entity
            properties = player_view.entity_properties[entity.entity_type]

            # Initialize a move and build action
            move_action = None
            build_action = None

            # If the entity can move, move it to the opposite corner of the map. Find closest position and break through set as true
            if properties.can_move:
                move_action = MoveAction(Vec2Int(player_view.map_size - 1, player_view.map_size - 1),True,True)

            # If the entity can't move, but can build, then execute
            elif properties.build is not None:

                # Gets the type of unit that the entity can make
                entity_type = properties.build.options[0]

                current_units = 0
                
                # Loop through all of the other entities in view
                for other_entity in player_view.entities:
                    # If they are owned by me, and are of the same type as the type that this entity can make, add one to current_units
                    if my_id == other_entity.player_id and other_entity.entity_type == entity_type:
                        current_units += 1

                # Check whether adding another unit is possible with the population we can provide for
                if (current_units + 1) * player_view.entity_properties[entity_type].population_use <= properties.population_provide:

                    # Set a build action to make a unit, putting in desired position of new entity
                    build_action = BuildAction(entity_type, Vec2Int(entity.position.x + properties.size, entity.position.y + properties.size - 1))
            
            # Sets the EntityAction for the entity. Prioritized as attack, build, repair, and move
            # For AttackAction, 
            # AttackAction(target entity's id or None, If specified, configures auto attacking)
            result.entity_actions[entity.id] = EntityAction(  
                move_action,
                build_action,

                # AutoAttack(maximum distance to pathfind, valid_targets)
                # Sets attack action as anything but resource for non-builders, and as resource for builders
                # If valid_targets is empty, then all types but resource are considered
                AttackAction(None, AutoAttack(properties.sight_range, [
                             EntityType.RESOURCE] if entity.entity_type == EntityType.BUILDER_UNIT else [])),
                None
            )
        return result

    def debug_update(self, player_view, debug_interface):
        debug_interface.send(DebugCommand.Clear())
        debug_interface.get_state()
