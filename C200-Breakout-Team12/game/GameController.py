# this module 'runs' a level of the game
# The NewGameLoader screen inits a new game self.state, and makes a
# Game screen for level 0. Each level, the self.stateManager is given
# a between-game-levels screen, and then a new Game screen for
# the next level.
# The GameScreen loads the level and calls this class's update()
# on each GameScreen update. This module updates the game self.state
# (it contains all game logic). Then, the GameScreen uses the
# GameRenderer to display the current game self.state.
# Name derived from the model-view-controller separation that
# is present here.
import random

import Graphics
import ScreenManager
from Assets import Assets
from GameConstants import *
from game.GameState import GameState
from game.LevelTools import makeBall
from game.gameClasses.Acceleration import Acceleration
from game.gameClasses.Ball import Ball
from game.gameClasses.Displayable import Displayable
from game.gameClasses.Paddle import Paddle
from game.gameClasses.PosCircle import PosCircle
from game.gameClasses.PosPoint import PosPoint
from game.gameClasses.Rotator import Rotator
from game.gameClasses.Velocity import Velocity


class GameController:
	def __init__(self, state: GameState):
		self.moveDir: int = 0
		self.state: GameState = state
		self.paddle: Paddle = state.paddle  # shortcut to avoid having to type self.state.paddle
		self.frame = 0

	def update(self, frame: int):

		# update these in case they changed
		self.paddle: Paddle = self.state.paddle  # shortcut to avoid having to type self.state.paddle
		self.frame = frame

		if self.state.paused:
			# let the paddle move even if the game hasn't started
			self.movePaddle()
			# but don't let it go off the screen
			self.collidePaddleWall()
			# and have the displayables continue moving
			self.updateDisplayables()
			self.state.collidedLastFrame = False
			# start the game when started
			# cant use pygame.mouse.get_pressed() because the user has to click to begin the game
			#   and so the mouse button will still be held down when the game loads, and it will
			#   immediately begin
			#  would be too complex to put the event loop here
			if pygame.key.get_pressed()[GC_KEY_BEGIN]:
				self.state.paused = False
			return

		self.state.time += GC_FRAME_TIME_SECONDS
		self.state.collidedLastFrame = False
		self.updateDisplayables()
		self.updateBall()
		self.movePaddle()
		self.collidePaddleWall()
		self.collideBrickBall()
		self.collidePaddleBall()
		self.score()

	def updateDisplayables(self):
		for d in self.state.displayables:
			d.acceleration.apply(d.velocity)
			d.velocity.apply(d.pos)
		self.state.displayables = list(
			filter(
				lambda displayable: self.frame < displayable.beginFrame + displayable.lifespan,
				self.state.displayables))

	def movePaddle(self):
		for e in pygame.event.get():
			if e.type == pygame.MOUSEMOTION:
				# ignore mouse input if in the embedded main menu game
				# but can't import MainMenuScreen
				if ScreenManager.currentScreen.__class__.__name__ != 'GameScreen':
					break
				x = e.pos[0]
				percent = x / Graphics.windowSurface.get_width()
				x = Graphics.surface.get_width() * percent
				x -= GC_PADDLE_WIDTH / 2
				self.paddle.rect.x = x
			if e.type == pygame.KEYDOWN:
				if e.key == pygame.K_LEFT:
					self.moveDir = -1
				if e.key == pygame.K_RIGHT:
					self.moveDir = 1
				# The GameScreen class needs to use event-driven input for the pause key
				# and can't poll for it, so post escape key down events back onto the queue.
				if e.key == pygame.K_ESCAPE:
					pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
			if e.type == pygame.KEYUP:
				if e.key == pygame.K_LEFT:
					if self.moveDir == -1:
						self.moveDir = 0
				if e.key == pygame.K_RIGHT:
					if self.moveDir == 1:
						self.moveDir = 0
		self.paddle.velocity.dx = self.moveDir * GC_PADDLE_SPEED
		self.paddle.velocity.apply(self.paddle.rect)

	def updateBall(self):
		self.state.lastPosBalls = []
		for i in range(len(self.state.balls)):
			# store last position
			self.state.lastPosBalls.append(PosPoint(self.state.balls[i].circle.x, self.state.balls[i].circle.y))
		for ball in self.state.balls:
			# move; update velocity before position
			halfAccel: Acceleration = Acceleration(ball.acceleration.ddx / 2, ball.acceleration.ddy / 2)
			halfAccel.apply(ball.velocity)
			ball.velocity.apply(ball.circle)
			halfAccel.apply(ball.velocity)

			# collide with walls and top/bottom of world
			wallCollided = 0
			if ball.circle.x - ball.circle.radius < GC_WALL_SIZE:
				ball.circle.x = GC_WALL_SIZE + ball.circle.radius
				ball.velocity.dx *= -1
				ball.circle.x = GC_WALL_SIZE + ball.circle.radius
				wallCollided = -1  # left
			elif ball.circle.x + ball.circle.radius > GC_WORLD_WIDTH - GC_WALL_SIZE:
				ball.circle.x = GC_WORLD_WIDTH - ball.circle.radius - GC_WALL_SIZE
				ball.velocity.dx *= -1
				ball.circle.x = GC_WORLD_WIDTH - GC_WALL_SIZE - ball.circle.radius
				wallCollided = 1  # right

			if wallCollided:  # add animation and screenflash
				# add screenflash
				self.state.collidedLastFrame = True
				# find the collision speed into the wall (dx only)
				collisionSpeed = abs(ball.velocity.dx)
				# add screenshake
				Graphics.camera.kick(collisionSpeed)
				# get the right collision strength based on speed (S, M, or L)
				if collisionSpeed <= 8:
					collisionIntensity = 'S'
				elif collisionSpeed <= 11:
					collisionIntensity = 'M'
				else:
					collisionIntensity = 'L'

				if wallCollided == -1:
					collisionDirection = "LEFT"
					collisionX = GC_WALL_SIZE
				else:
					collisionDirection = "RIGHT"
					collisionX = GC_WORLD_WIDTH - GC_WALL_SIZE
				self.state.displayables.append(
					Displayable(PosPoint(collisionX, ball.circle.y), Velocity(0, 0), Acceleration(0, 0),
								Rotator(0, 0, 0),
								getattr(Assets, "A_WALL_BOUNCE_" + collisionIntensity + "_" + collisionDirection),
								self.frame))

			# set 'won'
			if ball.circle.y - ball.circle.radius < 0:
				self.state.won = 1
			# decrement lives or set 'lost'
			elif ball.circle.y + ball.circle.radius > GC_WORLD_HEIGHT:
				# if this is the last ball...
				# if you had one life left, set won == -1
				# else, pause, regenerate the initial ball, decrement life
				if len(self.state.balls) == 1:
					if self.state.numLives == 1:
						self.state.won = -1
					else:
						self.state.paused = True
						self.state.balls = [makeBall()]
						self.state.numLives -= 1

				# add explosion animation, even if it wasn't the last ball
				# also screenshake
				Graphics.camera.kick(45)
				self.state.displayables.append(Displayable(
					PosPoint(ball.circle.x, GC_WORLD_HEIGHT),
					Velocity(0, 0),
					Acceleration(0, 0),
					Rotator(0, 0, 0),
					Assets.A_LOST_EXPLOSION,
					self.frame))
				# but if this isn't the last ball, just remove it from the list of balls
				# but remove it even if it is the last ball
				self.state.balls = list(
					filter(lambda b: b.circle.y < GC_WORLD_HEIGHT - b.circle.radius, self.state.balls))

	def collidePaddleWall(self):
		if self.paddle.rect.x < GC_WALL_SIZE:
			self.paddle.rect.x = GC_WALL_SIZE
		elif (self.paddle.rect.x + self.paddle.rect.width) > GC_WORLD_WIDTH - GC_WALL_SIZE:
			self.paddle.rect.x = GC_WORLD_WIDTH - GC_WALL_SIZE - self.paddle.rect.width

	def collidePaddleBall(self):
		# The ball's velocity (per frame) is a large percentage of the paddle height.
		# So find where it actually would have hit the paddle, not where it is
		# relative to the paddle on this frame.

		for i in range(len(self.state.balls)):
			ball = self.state.balls[i]
			if self.paddle.rect.intersectsCircle(ball.circle):
				largeY = ball.circle.y - self.state.lastPosBalls[i].y
				largeX = ball.circle.x - self.state.lastPosBalls[i].x
				smallY = GC_PADDLE_TOP_HEIGHT - self.state.lastPosBalls[i].y
				scale = smallY / largeY
				smallX = scale * largeX
				intersectX = smallX + self.state.lastPosBalls[i].x
				intersectPoint = PosPoint(intersectX, GC_PADDLE_TOP_HEIGHT)

				angle = self.paddle.rect.findAngle(intersectPoint)

				if angle < GC_PADDLE_UL_ANGLE or angle > GC_PADDLE_UR_ANGLE:
					self.state.collidedLastFrame = True
					# hit side of paddle
					ball.velocity.dx *= -1
				else:
					# hit top of paddle
					self.state.collidedLastFrame = True
					velocityMagnitude = (ball.velocity.dx ** 2 + ball.velocity.dy ** 2) ** 0.5
					xDiff = intersectPoint.x - (self.paddle.rect.x + self.paddle.rect.width // 2)
					xDiff /= self.paddle.rect.width // 2
					reflectAngle = 270 + xDiff * GC_MAX_BOUNCE_ANGLE
					velocityX = math.cos(math.radians(reflectAngle)) * velocityMagnitude
					velocityY = math.sin(math.radians(reflectAngle)) * velocityMagnitude
					ball.velocity.dx = velocityX
					ball.velocity.dy = velocityY

				# add screenshake
				Graphics.camera.kick(-ball.velocity.dy / 2)
				# add paddle electric animation
				# first, if ball hit paddle hard, do strong effect
				if ball.velocity.dy <= -GC_BALL_INITIAL_VELOCITY:
					self.state.paddle.image.switchTo(Assets.A_PADDLE_ELECTRIC_S, self.frame)
				else:
					# find angles to get left/middle/right starting point
					angleL = GC_PADDLE_UL_ANGLE
					angleML = GC_PADDLE_UL_ANGLE + (GC_PADDLE_UR_ANGLE - GC_PADDLE_UL_ANGLE) * (1 / 16)
					angleMR = GC_PADDLE_UL_ANGLE + (GC_PADDLE_UR_ANGLE - GC_PADDLE_UL_ANGLE) * (15 / 16)
					angleR = GC_PADDLE_UR_ANGLE
					if angleL <= angle < angleML:
						# left
						# THIS DOESN'T WORK!!! no idea why
						# The code does get executed, tested via print statements after all of these switchTo()s.
						# Middle, right, and strong animations work just fine, it's just the left that fails.
						self.paddle.image.switchTo(Assets.A_PADDLE_ELECTRIC_L, self.frame)
					elif angleML <= angle < angleMR:
						# middle
						self.paddle.image.switchTo(Assets.A_PADDLE_ELECTRIC_M, self.frame)
					elif angleMR <= angle <= angleR:
						# right
						self.paddle.image.switchTo(Assets.A_PADDLE_ELECTRIC_R, self.frame)
					else:
						# hit side of paddle, do strong effect
						self.paddle.image.switchTo(Assets.A_PADDLE_ELECTRIC_S, self.frame)

	def collideBrickBall(self):
		for ball in self.state.balls:
			# collision and HP removal
			for brick in self.state.bricks:
				if brick.rect.intersectsCircle(ball.circle):
					self.state.collidedLastFrame = True
					brick.hp -= 1
					if brick.hp != 0:  # don't bounce the ball when it destroys a brick
						# add screenshake
						Graphics.camera.kick(((ball.velocity.dx ** 2 + ball.velocity.dy ** 2) ** 0.5) / 4)
						# add dust animation
						self.state.displayables.append(Displayable(
							PosPoint(brick.rect.x + brick.rect.width // 2, brick.rect.y + brick.rect.height // 2),
							Velocity(ball.velocity.dx / 30, ball.velocity.dy / 15),
							Acceleration(0, GC_GRAVITY_ACCEL / 2), Rotator(0, 0, 0), Assets.A_BRICK_DUST,
							self.frame))
						# do the collision and bounce the ball
						angle = brick.rect.findAngle(ball.circle)
						if (angle >= GC_BRICK_UR_ANGLE or angle < GC_BRICK_BR_ANGLE or
								GC_BRICK_BL_ANGLE <= angle < GC_BRICK_UL_ANGLE):
							# hit side of brick
							ball.velocity.dx *= -1
							if ball.circle.x > brick.rect.x + .5 * GC_BRICK_WIDTH:
								ball.circle.x = brick.rect.x + GC_BRICK_WIDTH + ball.circle.radius
							else:
								ball.circle.x = brick.rect.x - ball.circle.radius
						else:
							# hit top of brick
							ball.velocity.dy *= -1
							if ball.circle.y > brick.rect.y + brick.rect.height:
								ball.circle.y = brick.rect.y + brick.rect.height + ball.circle.radius
							else:
								ball.circle.y = brick.rect.y - ball.circle.radius
					else:  # killed a brick, apply power up effects
						# add screenshake
						Graphics.camera.kick(((ball.velocity.dx ** 2 + ball.velocity.dy ** 2) ** 0.5) / 2)
						# add brick fragment animations:
						if GC_BRICK_FRAGS:
							for i in range(random.randint(GC_NUM_BRICK_FRAGMENTS[0], GC_NUM_BRICK_FRAGMENTS[1])):
								brickFragType = random.randint(1, Assets.NUM_BRICK_FRAG_TYPES)
								brickFragAngle = random.randint(0, 359)
								brickFragVelocity = random.randint(3, 6)
								brickFragR = random.randint(0, 359)
								brickFragDr = random.randint(20, 80)
								brickFragDdr = random.randint(0, 10)
								self.state.displayables.append(Displayable(
									PosPoint(brick.rect.x + brick.rect.width // 2,
											 brick.rect.y + brick.rect.height // 2),
									Velocity(brickFragVelocity * math.cos(math.radians(brickFragAngle)),
											 brickFragVelocity * math.sin(math.radians(brickFragAngle))),
									Acceleration(0, GC_GRAVITY_ACCEL),
									Rotator(brickFragR, brickFragDr, brickFragDdr),
									getattr(Assets, "A_BRICK_FRAG_" + str(brickFragType) + str(brick)),
									self.frame))
						if brick.powerUp == 'extraBall':
							angle = random.randint(0, 360)
							xVelocity = math.cos(math.radians(angle)) * GC_BALL_INITIAL_VELOCITY
							yVelocity = math.sin(math.radians(angle)) * GC_BALL_INITIAL_VELOCITY

							self.state.balls.append(Ball(
								PosCircle(brick.rect.x + brick.rect.width / 2, brick.rect.y + brick.rect.height / 2,
										  GC_BALL_RADIUS),
								Velocity(xVelocity, yVelocity)))
						if brick.powerUp == 'clearRow':
							rowHeight = brick.rect.y
							self.state.bricks = list(filter(lambda b: b.rect.y != rowHeight, self.state.bricks))
			# add score for dead bricks
			for brick in self.state.bricks:
				if brick.hp == 0:
					self.state.totalBricksDestroyedScore += brick.score

			# noinspection PyShadowingNames
			# remove dead bricks
			self.state.bricks = list(filter(lambda brick: brick.hp != 0, self.state.bricks))

	def score(self):  # the name of this method is a verb, not a noun
		if self.state.level == 99:  # main menu screen embedded level has no par time
			return 0
		score = GC_PAR_TIME[self.state.level - 1] / self.state.time
		percentBricksDestroyed = 0
		if not self.state.totalBrickScore == 0:  # don't divide by zero in case of 'empty' brick generation
			percentBricksDestroyed = self.state.totalBricksDestroyedScore / self.state.totalBrickScore
		score *= (1 - percentBricksDestroyed) + 100
		self.state.score = int(score)
