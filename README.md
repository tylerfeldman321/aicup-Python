# aicup-Python
Repo to hold code used for the aicup. This was a competition where individuals coded AI's to control a RTS / starcraft style game.

## Strategy
- In early game, my strategy focused on creating builders. Builders can mine materaisl and construct new buildings such as barracks for spawning new units and turrets for defense.
- In the middle game, I focused on building up the army of ranged and melee troops. The attacking units are commanded to move to the edge of the base and patrol, looking for any enemies that are attacking. This results in the army being built up while defending the base.
- During the late game, attacking units will be sent to destroy opponent bases. If they run into any enemy units, they will autotarget them. Once bases are destroyed, the units will find and target any remaining entities.
- Builders will first check if there are any buildings that need repair. If there are, then a certain number of builders will come to repair the building. If a builder is not tasked to repair anything, then it will go mine nearby resources.

## Code
- This code is quite messy and could be refactored to be much cleaner and to be much more easily modified.
- `my_strategy.py` contains the code to run the strategy described above.
