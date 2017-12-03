import GameConstants
import Graphics
import ScreenManager
from Assets import Assets
from GameConstants import *
from game.LevelTools import makeState
from screens.Screen import Screen


class BetweenLevelsScreen(Screen):
	def __init__(self, level, score, numLives):
		lifeToAdd = 0
		if level % 2 != 0:
			lifeToAdd = 1
		self.state = makeState(level + 1, score, numLives + lifeToAdd)

	def update(self):
		super().update()
		Graphics.clear(Assets.I_BLUR)
		Graphics.surface.blit(Assets.I_BETWEEN_LEVELS_BACKGROUND, (0, 0))
		Graphics.flip()
		if pygame.key.get_pressed()[GameConstants.GC_KEY_BEGIN]:
			from screens.GameScreen import GameScreen
			ScreenManager.setScreen(GameScreen(self.state))
