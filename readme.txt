====================================================
File created by Sam Kim:
"final deliverable\Project Files\Player and Game.py"
====================================================

Demonstration video:
https://streamable.com/01ow3

I wanted to simulate a real-life basketball game as close as I could.

I created a Game class that handles all the game's events such as:
-game/shot clock,
-a shot attempt
-a missed shot
-rebounding
-an attempt to pass the ball to a teammate
-drawing the court, players, and ball
-stats, box score, and play-by-play transcript
-drawing the start screen and pause screen
-assigning teams and matchups

I created a Player class the handles each individual player's events:
-on ball offense (loops thru various options: pass, shoot, drive, stand, move)
-off ball offense (move to new spots, which depend on a player's position)
-on ball defense (stay between the hoop and the matchup)
-off ball defense (stay between the ball and the matchup)