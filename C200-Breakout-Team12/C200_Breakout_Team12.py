# Alexander Moriarty, Sub Raizada, Kevin Tinsley
# CSCI-C 200
# Final Project: Breakout

# Type hints are used extensively in this project to help write better code faster.
# A few examples of their benefits:
# Code is self-documenting and easier to understand when reading later
# IDE will autocomplete better based on explicitly stated types
# IDE will show types in parameters popup when calling functions
# IDE will often generate warnings on using incorrect type

# Credits:
# Icon (assets/icon.png) taken from: https://github.com/bozidarsevo/sprite-kit-breakout
# The font used is Code Bold: http://www.fontfabric.com/code-free-font-3/


# The code starts below, where it says 'game starts here'
def start():
	# init pygame before importing/doing anything else
	import pygame
	pygame.init()

	# initialize display
	pygame.display.set_caption("Breakout!")
	pygame.display.set_icon(pygame.image.load("assets/icon.png"))
	# done initializing pygame, can import everything else now

	import Graphics  # import this first so graphics system is set up
	import ScreenManager
	from screens.LoadingScreen import LoadingScreen
	from GameConstants import GC_FULLSCREEN

	Graphics.goFullscreen() if GC_FULLSCREEN else Graphics.goWindowed()

	# start the game
	ScreenManager.currentScreen = LoadingScreen()
	ScreenManager.start()


###   GAME STARTS HERE   ######################################################
from GameConstants import GC_PROFILE

if GC_PROFILE:
	import cProfile

	cProfile.run('start()', sort="time")
else:
	start()
