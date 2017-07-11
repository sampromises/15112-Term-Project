#!/usr/bin/env python3

from tkinter import *
from eventBasedAnimationClass import EventBasedAnimationClass
import math
import random
import time
from tabulate import tabulate #https://pypi.python.org/pypi/tabulate

class Player(object):
    @staticmethod
    def getDistance(p1, p2):
        (x0, y0) = p1
        (x1, y1) = p2
        return ((y1-y0)**2 + (x1-x0)**2)**0.5

    @staticmethod
    def getSlope(p1, p2):
        (x0, y0) = p1
        (x1, y1) = p2
        if x1-x0 == 0: return None
        return (y1-y0) / (x1-x0)

    @staticmethod #adjusting radius depending on position
    def getPlayerRadius(position):
        avgRadius = (18.25/12) #average shoulder width for US man is 18.25"
        weights = [200,210,220,230,240]
        weight = weights[position-1]
        avgWeight = 220.0 #average weight in the NBA according to Wikipedia
        return (weight/avgWeight) * avgRadius

    @staticmethod #preset tendencies for each position
    def getTendencies(position):
        n = position - 1
        #corresponds to position + 1
        passBall = [5,3,3,2,2]
        shoot =    [2,5,3,3,2]
        drive =    [3,4,3,5,4]
        hold =     [2,3,3,4,5]
        move =     [3,3,3,2,3]
        tendencies = [passBall[n],shoot[n],drive[n],hold[n],move[n]]
        total = float(sum(tendencies))
        percentages = [n/total for n in tendencies]
        summ = 0
        finalList = []
        for i in range(len(percentages)):
            finalList.append(summ + percentages[i])
            summ += percentages[i]
        return finalList

    #Player attributes, tendencies, and state
    def __init__(self, selfAttributes, teamAttributes, game):
        self.game = game
        #specific to team
        self.oppHoop = teamAttributes['oppHoop']
        self.selfHoop = teamAttributes['selfHoop']
        self.teamName = teamAttributes['teamName']
        self.teamColor = teamAttributes['teamColor']
        #personal attributes
        self.name = selfAttributes['name']
        self.position = selfAttributes['position']
        self.speed = selfAttributes['speed']
        #state of Player in game
        self.hasBall = selfAttributes['hasBall']
        self.onOffense = teamAttributes['onOffense']
        self.onDefense = teamAttributes['onDefense']
        self.location = selfAttributes['location']
        self.inbounding = False
        self.inTransition = False if self.onDefense else True #initial settings
        #tendencies
        self.tendencies = Player.getTendencies(self.position)
        
        #Player's stats
        self.stats = {"PTS":0, "FGM":0, "FGA":0, "3PM":0, "3PA":0, "ORB":0, "DRB":0,
                     "TRB":0, "AST":0, "BLK":0, "STL":0, "TOV":0}
        self.sortedStatKeys = ["PTS", "FGM", "FGA", "3PM", "3PA", "ORB", "DRB",
                                "TRB", "AST", "BLK", "STL", "TOV"]
        self.r = Player.getPlayerRadius(self.position) * self.game.scale
        #player's direction, current location, and desired location (aka 'spot')
        (self.dx, self.dy) = (0, 0)
        self.spot = self.location
        #for accelerate() purposes
        self.startSpeed = 5 #default start speed (Vo)
        self.currentSpeed = self.startSpeed #current speed (Vf)
        self.startLocation = self.location #start location (Xo)

    #needed because players move in increments of their speed
    def canvasAlmostEqual(self, xy0, xy1):
        epsilon = self.currentSpeed
        return abs(xy1-xy0) <= epsilon

    #finding Vf with constant acceleration
    def accelerate(self):
        #Vf^2 = Vo^2 + 2ax
        Vo = self.startSpeed
        if self.game.userPlaying and self is self.game.user:
            a = self.speed * 1.2
        else:
            a = self.speed
        x = Player.getDistance(self.location, self.startLocation)
        self.currentSpeed = (Vo**2 + 2*a*x)**0.5

    #possible steal every time player bumps into a defender
    def possibleSteal(self, opp):
        stealChance = .01 / self.position
        if random.random() < stealChance:
            self.game.dialogue +="\n%s " % self.game.timestamp
            self.game.dialogue += "%s stole the ball out of %s's hands!" % (opp.name, self.name)
            self.hasBall = False
            opp.hasBall = True
            self.game.switchOffense()
            self.game.resetShotClock()
            self.stats['TOV'] += 1
            opp.stats['STL'] += 1
            return True
        else: return False

    #checks if a player bumps into another player
    def overlap(self, other):
        distance = Player.getDistance(self.location, other.location)
        r = (self.r + other.r)/2
        if distance < r:
            return True
        else:
            return False

    #check if in court boundaries
    def inBounds(self):
        r = self.r
        (x, y) = self.location
        #if x-r < self.game.margin or x+r > self.game.margin+self.game.courtWidth:
        if (self.canvasAlmostEqual(x-r, self.game.margin) or
            self.canvasAlmostEqual(x+r,self.game.margin+self.game.courtWidth)):
            return False
        #elif y-r < self.game.margin or y+r > self.game.margin+self.game.courtHeight:
        elif (self.canvasAlmostEqual(y-r, self.game.margin) or
            self.canvasAlmostEqual(y+r,self.game.margin+self.game.courtHeight)):
            return False

        return True

    #looks at current direction and changes location
    def move(self):
        self.accelerate()
        (x, y) = self.location

        #incorporating the speed of a player in his movement
        (dx, dy) = (self.dx*self.currentSpeed, self.dy*self.currentSpeed)
        
        self.location = (x + dx, y + dy)
        #back-tracking if out of bounds
        if not self.inBounds():
            self.spot = (x - dx, y - dy)
        #checking if bumping into opponents
        for opp in self.opponents:
            if self.overlap(opp):
                #if ball is stolen, stop the loop
                if (self.hasBall and opp.onDefense and self.possibleSteal(opp)):
                        break
                randomDirection = random.choice([-1,1])
                self.location = (x, y+randomDirection*self.currentSpeed)
                self.spot = (x - dx, y - dy)

    #checks if a player has arrived at his spot
    def atSpot(self):
        (selfx, selfy) = self.location
        (spotx, spoty) = self.spot
        if self.canvasAlmostEqual(selfx, spotx) and self.canvasAlmostEqual(selfy,spoty):
            self.startLocation = self.location
            return True
        else:
            return False

    #moves a player to the spot he is assigned to
    def moveToSpot(self):
        (selfx, selfy) = self.location
        (spotx, spoty) = self.spot

        angle = math.atan2((spoty-selfy) , (spotx-selfx))

        (self.dx, self.dy) = 1.0*math.cos(angle), 1.0*math.sin(angle)

        if not self.atSpot(): self.move()


    #using angles to determine if player can drive towards the hoop
    def openLane(self, other):
        (oppx, oppy) = other.location
        (hx, hy) = self.oppHoop
        
        #using law of cosines to find angle of defender and hoop
        a = Player.getDistance((hx,hy), (oppx,oppy))
        b = self.r + other.r
        c = (a**2 + b**2)**0.5
        #try/except in case of arccos Domain error
        try: oppAngle = math.acos((b**2-a**2-c**2) / (-2*a*c))
        except: oppAngle = 0
        #again, but with self
        (selfx, selfy) = self.location
        b = Player.getDistance((oppx,oppy), (selfx,selfy))
        c = Player.getDistance((selfx,selfy), (hx,hy))
        try: selfAngle = math.acos((b**2-a**2-c**2) / (-2*a*c))
        except: selfAngle = 0

        #if there is an angle to drive, or if Player is already past opponent
        if selfAngle > oppAngle or c < a:
            return True
        else:
            return False

    #driving (getting closer to hoop)
    def drive(self):
        (selfx, selfy) = self.location
        (hx, hy) = self.oppHoop
        self.spot = self.oppHoop
        x = selfx - hx
        y = selfy - hy
        angle = math.tan(y/x)

        direction = -1.0 if self in self.game.teamOne else 1.0

        #always try to shoot a lay-up if you get close enough (2 ft.)
        layupDistance = 2.0 * self.game.scale
        if Player.getDistance((selfx, selfy), (hx,hy)) < layupDistance:
            self.shoot()

    #checks if Player is 'open' for a jumpshot
    def openForShot(self):
        #really close to basket also counts as open
        veryClose = 5.0 * self.game.scale #5 ft.
        if Player.getDistance(self.location, self.oppHoop) < veryClose:
            return True
        #http://analyticsgame.com/nba/stat-exploration-modeling-field-goal-percentage.html
        openDistance = 3.0 * self.game.scale #3 ft. based on stats from link above
        for opponent in self.opponents:
            oppDistance = Player.getDistance(self.location, opponent.location)
            shotDistance = Player.getDistance(self.location, self.oppHoop)
            #4s and 5s don't shoot three pointers
            if self.position < 4: shotRange = self.game.hoopToTop3 + 2*openDistance
            else: shotRange = 17.5 * self.game.scale
            #if opponent is too close or if Player is too far = not Open
            if oppDistance < openDistance or shotDistance > shotRange:
                return False
        return True

    #checks if shot is a three pointer
    def isThreePointer(self):
        (x, y) = self.location
        (hx, hy) = self.oppHoop
        corner3x = self.game.margin + self.game.corner3Length
        #checking corner 3-pointers
        if (self in self.game.teamOne and x < corner3x or
            self in self.game.teamTwo and x > (self.game.width-corner3x)):
            if (y < (hy-self.game.hoopToCorner3) or
                y > (hy+self.game.hoopToCorner3)):
                return True
        #checking arc 3-pointer
        else:
            top3Distance = self.game.hoopToTop3
            shotDistance = Player.getDistance(self.location,self.oppHoop)
            if shotDistance > top3Distance:
                return True
        return False

    #shot blocked; ball goes to random player
    def blockedShot(self):
        #choosing random player
        randomPlayer = random.randint(0,len(self.game.players)-1)
        rebounder = self.game.players[randomPlayer]
        self.hasBall = False
        rebounder.rebound()
        #switch sides if rebounder is on the other team
        if rebounder in self.opponents:
            self.game.switchOffense()

    #shoot the ball; FGP dependent on how open you are and how far
    def shoot(self):
        self.game.dialogue +="\n%s %s shot the ball..." % (self.game.timestamp,  self.name)
        #adjusting stats and state
        isThree = self.isThreePointer()
        if isThree: self.stats["3PA"] += 1
        self.stats["FGA"] += 1
        self.hasBall = False
        
        #checking if shot is blocked
        blockChance = .1 * self.position #bigger players have higher chance of blocking shot
        for opp in self.opponents:
            if self.overlap(opp):
                if random.random() < blockChance:
                    self.game.dialogue += "and had it blocked by " + opp.name +"!"
                    opp.stats['BLK'] += 1
                    self.blockedShot()
                    return

        #(http://analyticsgame.com/nba/stat-exploration-modeling-field-goal-percentage.html)
        #Field Goal Percentage as a function of shot distance and defender distance 
        shotDistance = Player.getDistance(self.location, self.oppHoop) / self.game.scale
        oppDistance = Player.getDistance(self.location, self.matchup.location) / self.game.scale    
        FGP = ( 67.6 - 1.05 *  shotDistance)/(1 + math.e**( -( 0.273 * oppDistance + 0.349)))/100

        if random.random() < FGP:
            if isThree:
                self.game.dialogue += "and made a three!"
                self.stats["PTS"] += 3
                self.stats["3PM"] += 1
            else:
                self.game.dialogue += "and made the shot."
                self.stats["PTS"] += 2
            self.stats["FGM"] += 1
            #'passing' to the hoop; to make the animation
            self.game.ballLocation = self.location
            self.game.passRecipient = Hoop(self.game.hoopRadius, False)
            self.game.ballEnd = self.oppHoop
            self.game.ballBeingPassed = True
        else:
            self.game.dialogue += "and missed it."
            #'passing' to the hoop; to make the animation
            self.game.ballLocation = self.location
            self.game.passRecipient = Hoop(self.game.hoopRadius, True)
            (hx, hy) = self.oppHoop
            self.game.ballEnd = (hx, hy)
            self.game.ballBeingPassed = True

    #Player either passes, shoots, drives, holds, or moves
    #dependent on tendencies, which are based on Player's position
    def onBallOffense(self):
        passTendency = self.tendencies[0] 
        shootTendency = self.tendencies[1]
        driveTendency = self.tendencies[2]
        holdTendency = self.tendencies[3]
        moveTendency = self.tendencies[4]

        chance = random.random()

        if chance < passTendency:
            self.bestPassPossible()
        elif chance < shootTendency:
            if self.openForShot():
                self.shoot()
        elif chance < driveTendency:
            if self.openLane(self.matchup):
                self.drive()
        elif chance < holdTendency:
            self.spot = self.location
        else:
            self.spot = self.newSpot()

    #checking if a teammate is open; passing if he is
    def tryPassToTeammate(self, teammate):
        (x0, y0) = self.location
        (x1, y1) = teammate.location
        #http://stackoverflow.com/questions/13242738/how-can-i-find-the-general-form-equation-of-a-line-from-two-points
        a = (y0 - y1)
        b = (x1 - x0)
        c = (x0-x1)*y0 + (y1-y0)*x0

        teammateOpp = teammate.matchup
        (oppx, oppy) = teammateOpp.location
        #http://www.intmath.com/plane-analytic-geometry/perpendicular-distance-point-line.php
        d = abs(a*oppx + b*oppy + c) / (a**2+b**2)**0.5
        (oppx, oppy) = self.matchup.location
        d2 = abs(a*oppx + b*oppy + c) / (a**2+b**2)**0.5

        #must be able to pass the ball past own defender and teammate's defender
        if d > teammateOpp.r and d2 > self.matchup.r:
            self.hasBall = False
            self.game.ballLocation = (x0,y0)
            self.game.passer = self
            self.game.passRecipient = teammate
            self.game.ballEnd = (x1,y1)
            self.game.ballBeingPassed = True
            return True
        else:
            return False

    #going through own team and passing to best option
    def bestPassPossible(self):
        #sorting teammates by distance to hoop
        hoopLocation = self.oppHoop
        teammatesByDistance = sorted(self.teammates, 
            #lambda a, b: cmp(Player.getDistance(a.location,hoopLocation),
            #                    Player.getDistance(b.location,hoopLocation)))
            # 2to3 fix
            key = lambda a:Player.getDistance(a.location,hoopLocation) )
        for teammate in teammatesByDistance:
            if teammate is self: continue
            else:
                if self.tryPassToTeammate(teammate): break

    #for offBallOffense - ball either in players hands or in hoop
    def getBallLocation(self):
        for player in self.game.players:
            if player.hasBall:
                return player.location
        if self.onDefense: return self.oppHoop
        else: return self.selfHoop

    #determining spot to go to depending on position
    def newSpot(self):
        if self.position == 1:
            rowTerritory = range(5)
            colTerritory = [3, 4]
        elif self.position == 2:
            rowTerritory = [0, 1]
            colTerritory = [0, 1, 2]
        elif self.position == 3:
            rowTerritory = [3, 4]
            colTerritory = [0, 1, 2]
        elif self.position == 4:
            rowTerritory = [1, 2, 3]
            colTerritory = [1, 2]
        elif self.position == 5:
            rowTerritory = [1, 2, 3]
            colTerritory = [0, 1]

        randRow = random.choice(rowTerritory)
        randCol = random.choice(colTerritory)
        if self in self.game.teamTwo:
            randRow = abs(randRow - 4)
            randCol = abs(randCol - 4)

        #picking random coordinates in area
        (x0, x1) = self.xSpots[randCol]
        (y0, y1) = self.ySpots[randRow]
        margin = math.ceil(self.r)
        randX = random.randint(margin+x0, x1-margin)
        randY = random.randint(margin+y0, y1-margin)
        return (randX, randY)

    #trying to get open
    def offBallOffense(self):
        moveProb = float(1)/3 #moving to a new spot only 1/3 of the time
        if self.atSpot():
            if random.random() < moveProb:
                self.spot = self.newSpot()

    #Player rebounds the ball
    def rebound(self):
        #change user to rebounder
        if self in self.game.teamOne and self.game.userPlaying:
            self.game.user = self
        (time, name) = (self.game.timestamp, self.name)
        if self.onOffense:
            self.stats["ORB"] += 1
            reboundDialogue =  "\n%s %s got the offensive rebound!" % (time, name)
        else:
            self.stats["DRB"] += 1
            reboundDialogue =  "\n%s %s got the rebound." % (time, name)
        self.game.dialogue += reboundDialogue
        self.stats["TRB"] += 1
        self.hasBall = True

    #find defensive spot: between hoop and offensive Player
    def onBallDefense(self):
        (selfx, selfy) = self.location
        (oppx, oppy) = self.matchup.location
        (hx, hy) = self.selfHoop

        oppDistance = Player.getDistance((oppx,oppy),(hx,hy))
        spotDistance = (oppDistance*self.game.scale) ** 0.45
        #getting angle between hoop and opponent
        angle = math.atan((oppy-hy)/(oppx-hx))
        if self in self.game.teamOne: spotDistance *= -1
        spotx = oppx - spotDistance*math.cos(angle)
        spoty = oppy - spotDistance*math.sin(angle)

        self.spot = (spotx, spoty)

    #find defensive spot: between ball and offensive Player
    def offBallDefense(self):
        #if opponent is inbounding, wait for him at half-court
        if self.matchup.inbounding:
            (x,y) = (int(self.game.cx), int(self.game.cy))
            (xr, yr) = (int(self.game.circleR), self.game.courtHeight)
            randx = random.randint(x-xr,x+xr)
            randy = random.randint(y-yr,y+yr)
            self.spot = (randx,randy)
            return
        (selfx, selfy) = self.location
        (oppx, oppy) = self.matchup.location
        (hx, hy) = self.selfHoop
        (ballx, bally) = self.getBallLocation()

        oppDistance = Player.getDistance((oppx,oppy),(ballx, bally))
        spotDistance = (oppDistance*self.game.scale) ** 0.485 
        #angle between opponent and ball
        angle = math.atan2((bally-oppy),(ballx-oppx))
        spotx = oppx + spotDistance*math.cos(angle)
        spoty = oppy + spotDistance*math.sin(angle)

        self.spot = (spotx, spoty)

    #Player inbounding the ball
    def inboundBall(self):
        #if user is playing
        if self is self.game.user and self.game.userPlaying:
            shotClock = (self.game.shotClockTime - self.game.shotClock)
            #remind user to go inbound the ball
            if (19.9 < shotClock < 20.1):
                self.game.dialogue += "\nUser needs to inbound the ball!"
            (x, y) = self.location
            (hx, hy) = self.selfHoop
            #give user ball when he reaches the hoop
            if (self.canvasAlmostEqual(x, hx) and 
                self.canvasAlmostEqual(y, hy)):
                self.inbounding = False
                self.game.ballInHoop = False
                self.hasBall = True
        #going to inbound the ball
        else:
            self.spot = self.selfHoop
            if self.atSpot():
                self.inbounding = False
                self.game.ballInHoop = False
                self.hasBall = True
                self.inTransition = True

    #trying to pass to a guard (positions 1/2)
    def passToAGuard(self):
        guards = self.teammates[0:2]
        for guard in guards:
            if self.tryPassToTeammate(guard):
                self.inTransition = False
            else:
                self.spot = self.newSpot()

    #trying to get the ball as a guard
    def getBallAsGuard(self):
        if not self.hasBall:
            self.spot = self.newSpot()

    #which decision path to follow based on current state
    def makeTransitionDecision(self):
        #inbound the ball
        if self.inbounding:
            self.inboundBall()
        #transition from defense to offense
        elif self.inTransition:
            #pass it to a guard
            if self.position > 2 and self.hasBall:
                self.passToAGuard()
            #get the ball as a guard if a guard doesn't have it
            elif (self in self.teammates[0:2] and 
                not (self.teammates[0].hasBall or self.teammates[1].hasBall)):
                self.getBallAsGuard()
            #everyone else, get to the other side of the court
            else:
                selfx = self.location[0]
                halfCourt = self.game.margin + self.game.courtWidth/2
                if self in self.game.teamOne:
                    if selfx > halfCourt:
                        self.spot = self.newSpot()
                    else:
                        self.inTransition = False
                else:
                    if selfx < halfCourt:
                        self.spot = self.newSpot()
                    else:
                        self.inTransition = False
    
    #onOffense         
    def makeOffensiveDecision(self):
        if self.hasBall: self.onBallOffense()
        else: self.offBallOffense()

    #onDefense
    def makeDefensiveDecision(self):
        if self.matchup.hasBall: self.onBallDefense()
        else: self.offBallDefense()

    #drawing self, given Game's canvas
    def drawSelf(self, canvas):
        (selfx, selfy) = self.location
        (hx, hy) = self.oppHoop
        r = self.r
        teamColor = self.teamColor
        canvas.create_oval(selfx-r,selfy-r,selfx+r,selfy+r, width=0, fill = teamColor)
        if self.hasBall:
            ballR = self.game.ballR
            direction = -1.0 if self in self.game.teamOne else 1.0
            ballcx = selfx + direction*r*math.cos(math.pi/4)
            ballcy = selfy + direction*r*math.sin(math.pi/4)
            canvas.create_oval(ballcx-ballR,ballcy-ballR,ballcx+ballR,ballcy+ballR,
                                width = None, fill = 'orange')

        #drawing position
        size = self.game.scale
        canvas.create_text(selfx, selfy, text = str(self.position), font = ('Arial', size, 'normal'))
        #if the user is playing, create a label
        if self is self.game.user and self.game.userPlaying:
            lastName = "USER"
        else:
            lastName = self.name.split()[1]
        canvas.create_text(selfx,selfy+r,anchor=N,font=('Arial', size, 'normal'),text=lastName)

#for purposes of drawing the ball being 'passed' to the Hoop
class Hoop(Player):
    def __init__(self, r, missedShot):
        self.r = r
        self.missedShot = missedShot

#draws board, handles score, time, balls being passed, and interface
class Game(EventBasedAnimationClass):
    #Model function in MVC
    def __init__(self, scale):
        scale = int(scale)
        self.margin = 5 * scale
        self.rightMargin = 30 * scale
        self.scale = scale
        #court dimensions from http://www.sportsknowhow.com/basketball/dimensions/nba-basketball-court-dimensions.html
        self.courtWidth = 94.0 * scale
        self.courtHeight = 50.0 * scale
        self.circleR = 6.0 * scale
        self.hoopDistance = 4.0 * scale
        self.hoopRadius = 9.0/12.0 * scale
        self.backboardHeight = 6.0 * scale
        self.keyWidth = 19.0 * scale
        self.keyHeight = 16.0 * scale
        self.hoopToCorner3 = 22.0 * scale
        self.corner3Length = 13.7 * scale
        self.hoopToTop3 = 23.75 * scale
        self.ballR = (4.7/12.0) * scale
        super(Game, self).__init__(self.courtWidth+2*self.margin + self.rightMargin, self.courtHeight+2*self.margin)
        #center location and hoop locations
        (self.cx,self.cy) = (self.margin+(self.courtWidth/2),self.margin+self.courtHeight/2)
        self.hoopOne = (self.margin + self.hoopDistance + self.hoopRadius, self.height/2)
        self.hoopTwo = (self.width - self.rightMargin - self.hoopOne[0], self.hoopOne[1])
        #court colors
        self.primaryCourtColor = 'burlywood1'
        self.secondaryCourtColor = 'burlywood4'

    #Model function in MVC (also called to reset)
    def initAnimation(self):
        #offense team
        p1Attributes = {"name":"Chris Paul", "position":1, "speed":0.6, 'hasBall':True,'location':(0,0)}
        p2Attributes = {"name":"Kobe Bryant", "position":2, "speed":0.5, 'hasBall':False,'location':(0,0)}
        p3Attributes = {"name":"Kevin Durant", "position":3, "speed":0.4, 'hasBall':False,'location':(0,0)}
        p4Attributes = {"name":"LeBron James", "position":4, "speed":0.3, 'hasBall':False,'location':(0,0)}
        p5Attributes = {"name":"Tyson Chandler", "position":5, "speed":0.2, 'hasBall':False,'location':(0,0)}

        #defense team
        p6Attributes = {"name":"Magic Johnson", "position":1, "speed":0.6, 'hasBall':False,'location':(0,0)}
        p7Attributes = {"name":"Michael Jordan","position":2, "speed":0.5, 'hasBall':False,'location':(0,0)}
        p8Attributes = {"name":"Larry Bird", "position":3, "speed":0.4, 'hasBall':False,'location':(0,0)}
        p9Attributes = {"name":"Charles Barkley", "position":4, "speed":0.3, 'hasBall':False,'location':(0,0)}
        p10Attributes = {"name":"Karl Malone", "position":5, "speed":0.2, 'hasBall':False,'location':(0,0)}
        
        self.teamOneAttributes = {"teamName":"2012 Dream Team","teamColor":"red",
                                    "selfHoop":self.hoopTwo, "oppHoop":self.hoopOne,
                                    'onOffense':True, 'onDefense':False}

        self.teamTwoAttributes = {"teamName":"1992 Dream Team","teamColor":"lightBlue",
                                    "selfHoop":self.hoopOne, "oppHoop":self.hoopTwo,
                                    'onOffense':False, 'onDefense':True}
        #team one
        p1 = Player(p1Attributes, self.teamOneAttributes, self)
        p2 = Player(p2Attributes, self.teamOneAttributes, self)
        p3 = Player(p3Attributes, self.teamOneAttributes, self)
        p4 = Player(p4Attributes, self.teamOneAttributes, self)
        p5 = Player(p5Attributes, self.teamOneAttributes, self)
        #team two
        p6 = Player(p6Attributes, self.teamTwoAttributes, self)
        p7 = Player(p7Attributes, self.teamTwoAttributes, self)
        p8 = Player(p8Attributes, self.teamTwoAttributes, self)
        p9 = Player(p9Attributes, self.teamTwoAttributes, self)
        p10 = Player(p10Attributes, self.teamTwoAttributes, self)

        #assigning teams and match-ups
        self.players = [p1,p2,p3,p4,p5,p6,p7,p8,p9,p10]
        self.teamOne = []
        self.teamTwo = []
        self.setTeams()
        self.setMatchups()
        self.spawnAroundCircle()

        #initial game state
        self.ballInHoop = False
        self.setSpots()
        self.dialogue = """\nGame start!"""
        self.inMenu = True #starts in menu
        self.gameOver = False
        self.paused = False
        self.ballBeingPassed = False
        self.rebounder = None
        #game clock and shot clock using time module
        self.stopClock = False
        self.startTime = time.time()
        self.gameClock = 0 #initial value (goes from 0 - end)
        self.shotClockStartTime = time.time()
        self.shotClockTime = 24
        self.shotClock = 0 #initial value (goes from 0 - 24)
        self.pauseStartTime = time.time() #game starts 'paused'
        self.pausedTime = 0 #one paused time interval
        self.totalPausedTime = 0 #total time paused
        #can be changed to make game longer/shorter
        self.endGameTime = 10 * 60 #10 minutes (in seconds)
        self.overtimeTime = 2 * 60 #2 minutes (in seconds)
        self.gameoverPrinted = False
        #for assist counting
        self.passer = None
        self.passTime = 0
        #user can play as Player 1
        self.userPlaying = False
        self.user = self.players[0]
        #Game speed settings
        self.tempo = 50 #offensive tempo (0-100)
        self.timerDelay = 50

        #loading start image
        self.photo = PhotoImage(file="kobe.gif")

    #sets initial player locations around half-court
    def spawnAroundCircle(self):
        (cx, cy) = ((self.width-self.rightMargin)/2, self.height/2)
        r = self.circleR*3
        angle = math.pi/2
        for player in self.teamOne:
            angle -= (2*math.pi)/10
            player.location = (cx+r*math.cos(angle), cy-r*math.sin(angle))
        for player in reversed(self.teamTwo):
            angle -= (2*math.pi)/10
            player.location = (cx+r*math.cos(angle), cy-r*math.sin(angle))

    #sets teams based on initial offense/defense alignment
    def setTeams(self):
        for player in self.players:
            if player.teamName == self.teamOneAttributes['teamName']:
                self.teamOne.append(player)
            else:
                self.teamTwo.append(player)

        for player in self.players:
            if player.teamName == self.teamOneAttributes['teamName']:
                teammates = self.teamOne
                opponents = self.teamTwo
            else:
                teammates = self.teamTwo
                opponents = self.teamOne
            player.teammates = teammates
            player.opponents = opponents

    #assigns each player a match-up based on position
    def setMatchups(self):
        for playerOne in self.teamOne:
            for playerTwo in self.teamTwo:
                if playerOne.position == playerTwo.position:
                    playerOne.matchup = playerTwo
                    playerTwo.matchup = playerOne

    #flips Offense <->Defense
    def switchOffense(self):
        for player in self.players:
                player.onOffense = not player.onOffense
                player.onDefense = not player.onDefense
                player.spot = player.location #freeze player
                if player.onOffense: player.inTransition = True
                else: player.inTransition = False

    #finds a rebounder based on distance
    def getRebounder(self):
        closestPlayer = None
        closestDistance = self.courtWidth
        hoopLocation = self.hoopOne if self.teamOne[0].onOffense else self.hoopTwo
        for player in self.players:
            #offensive rebound chance
            offensiveReboundChance = .05 * player.position #bigger, higher chance
            if player.onOffense:
                if random.random() < offensiveReboundChance: pass
                else: continue

            distance = Player.getDistance(player.location, hoopLocation)
            if distance < closestDistance:
                closestPlayer = player
                closestDistance = distance

        return closestPlayer

    #in the event of a made shot
    def madeShot(self):
        #reward assist, if there was one
        assistWindow = 2.5 #2.5 seconds for an assist
        if ((time.time()-self.passTime-self.totalPausedTime) < assistWindow
            and self.passer != None and not isinstance(self.passer, Hoop)):
            self.passer.stats['AST'] += 1
            self.dialogue += "\n(%s got the assist.)" % self.passer.name
        self.resetShotClock()
        self.ballInHoop = True
        self.switchOffense()
        #point guard always inbounding
        if self.teamOne[0].onOffense: self.teamOne[0].inbounding = True
        else: self.teamTwo[0].inbounding = True
        #transcripting current score
        (oneScore,twoScore) = self.getScores()
        oneName = self.teamOneAttributes['teamName']
        twoName = self.teamTwoAttributes['teamName']
        self.dialogue += "\n\n %s[%d] - %s[%d] \n" % (oneName,oneScore,twoName,twoScore)

    #in the event of a made shot
    def missedShot(self):
        self.resetShotClock()
        self.rebounder.rebound()
        #either defensive or offensive rebound
        if self.rebounder.onDefense:
            self.switchOffense()

    #implementing of the ball being moved around court
    def passBall(self):
        if not isinstance(self.passRecipient, Hoop):
            self.passTime = time.time() - self.totalPausedTime
        ballSpeed = 60
        (x0, y0) = self.ballLocation
        (x1, y1) = self.ballEnd
        r = self.passRecipient.r

        distance = ((y1-y0)**2 + (x1-x0)**2)**0.5
        if distance <= (r + ballSpeed):
            self.ballBeingPassed = False
            if isinstance(self.passRecipient, Hoop):
                #'passing' to the rebounder, now
                if self.passRecipient.missedShot:
                    self.rebounder = self.getRebounder()
                    self.ballEnd = self.rebounder.location
                    self.passRecipient = self.rebounder
                    self.ballBeingPassed = True
                else:
                    self.madeShot()
            else:
                if self.rebounder != None:
                    self.missedShot()
                    self.rebounder = None
                    return
                else:
                    self.passRecipient.hasBall = True
        else:
            defenseTeam = self.teamTwo if self.teamTwo[0].onDefense else self.teamOne
            for opp in defenseTeam:
                r = self.ballR + opp.r
                stealChance = .05 / opp.position #smaller defenders have higher steal chance
                if (opp.getDistance(self.ballLocation,opp.location) < r 
                    and random.random()<stealChance):
                    self.dialogue +=  "\n%s %s stole the ball!"  % (self.timestamp, opp.name)
                    self.switchOffense()
                    opp.hasBall = True
                    self.passer.stats['TOV'] += 1
                    opp.stats['STL'] += 1
                    self.passRecipient.hasBall = False
                    self.resetShotClock()
                    self.ballBeingPassed = False

        angle = math.atan2((y1-y0),(x1-x0))
        (dx, dy) = (1.0*math.cos(angle), 1.0*math.sin(angle))
        (bx, by) = self.ballLocation
        self.ballLocation = (bx + dx*ballSpeed, by + dy*ballSpeed)

    #drawing the ball if it's being passed or shot
    def drawBall(self):
        (bx, by) = self.ballLocation
        r = self.ballR
        self.canvas.create_oval(bx-r,by-r,bx+r,by+r,fill='orange')

    #drawing the court boundaries
    def drawCourt(self):
        #yellow background
        self.canvas.create_rectangle(0,0,self.width,self.height,fill='white')
        #drawing court bounds
        (x0, y0) = (self.margin, self.margin)
        self.canvas.create_rectangle(x0,y0,x0+self.courtWidth,y0+self.courtHeight,
                                    width = 2, fill = self.primaryCourtColor)

        #drawing half-court line
        self.canvas.create_line(self.margin+self.courtWidth/2,self.margin,
                                self.margin+self.courtWidth/2,self.margin+self.courtHeight)

        #drawing half-court circle
        (cx, cy) = ((self.width-self.rightMargin)/2, self.height/2)
        circleR = self.circleR
        self.canvas.create_oval(cx-circleR,cy-circleR,cx+circleR,cy+circleR,
                                width = 2, fill = self.secondaryCourtColor)
        
        #drawing the key
        (keyx, keyy) = (self.margin, self.height/2 - self.keyHeight/2)
        self.canvas.create_rectangle(keyx,keyy,keyx+self.keyWidth,keyy+self.keyHeight,
                                    width = 2, fill = self.secondaryCourtColor)
        keyx = self.width-self.rightMargin-self.margin
        self.canvas.create_rectangle(keyx,keyy,keyx-self.keyWidth,keyy+self.keyHeight,
                                    width = 2, fill = self.secondaryCourtColor)

        #drawing semi-circles at top of key
        (keyx0, keyy0) = (self.margin+self.keyWidth-circleR, self.height/2-circleR)
        (keyx1, keyy1) = (keyx0+2*circleR, keyy0+2*circleR)
        self.canvas.create_arc(keyx0,keyy0,keyx1,keyy1, start = 90, extent = -180, width = 2)
        arcSegments = 14
        arcStart = 90
        arcIncrement = 180 / arcSegments
        for i in range(arcSegments):
            if i%2 == 1:
                self.canvas.create_arc(keyx0,keyy0,keyx1,keyy1, start = arcStart,
                    extent = arcIncrement, width = 2, style = ARC)
            arcStart += arcIncrement

        (keyx0, keyy0) = (self.width-self.rightMargin-
                            self.margin-self.keyWidth-circleR, self.height/2-circleR)
        (keyx1, keyy1) = (keyx0+2*circleR, keyy0+2*circleR)
        self.canvas.create_arc(keyx0,keyy0,keyx1,keyy1, start = 90, extent = 180, width = 2)
        arcSegments = 14
        arcStart = 90
        arcIncrement = -180 / arcSegments
        for i in range(arcSegments):
            if i%2 == 1:
                self.canvas.create_arc(keyx0,keyy0,keyx1,keyy1, start = arcStart,
                    extent = arcIncrement, width = 2, style = ARC)
            arcStart += arcIncrement

        #drawing corner three-point lines
        (hoopx, hoopy) = self.hoopOne
        (corner3x, corner3y) = (self.margin, hoopy - self.hoopToCorner3)
        for line in range(2):
            self.canvas.create_line(corner3x,corner3y,
                                    corner3x + self.corner3Length,corner3y, width = 2)
            corner3y += 2*self.hoopToCorner3
        (corner3x, corner3y) = (self.width-self.rightMargin-self.margin, hoopy - self.hoopToCorner3)
        for line in range(2):
            self.canvas.create_line(corner3x,corner3y,
                                    corner3x - self.corner3Length,corner3y, width = 2)
            corner3y += 2*self.hoopToCorner3
            
        #drawing top three-point arc
        threeR = self.hoopToTop3
        angleOffset = 22 #hard-coded after trial/error on tkinter canvas
        self.canvas.create_arc(hoopx-threeR, hoopy-threeR, hoopx+threeR, hoopy+threeR,
                                start = 90-angleOffset, extent = -180+2*angleOffset,
                                width = 2, style = ARC)
        (hoopx, hoopy) = self.hoopTwo
        self.canvas.create_arc(hoopx-threeR, hoopy-threeR, hoopx+threeR, hoopy+threeR,
                                start = 90+angleOffset, extent = 180-2*angleOffset,
                                width = 2, style = ARC)

    #drawing the hoops
    def drawHoops(self):
        hoopR = self.hoopRadius
        ballR = self.ballR
        (hoopx, hoopy) = self.hoopOne
        self.canvas.create_oval(hoopx-hoopR,hoopy-hoopR,hoopx+hoopR,hoopy+hoopR,
                                width=2, outline='orange')
        if self.teamOne[0].onDefense and self.ballInHoop:
            self.canvas.create_oval(hoopx-ballR,hoopy-ballR,hoopx+ballR,hoopy+ballR,
                                    width=0,fill='orange')
        #drawing the backboard
        (boardX, boardY) = (self.margin + self.hoopDistance,
                            self.height/2 - self.backboardHeight/2)
        self.canvas.create_line(boardX,boardY,boardX,boardY+self.backboardHeight,
                                width = 2, fill = 'grey')

        (hoopx, hoopy) = self.hoopTwo
        self.canvas.create_oval(hoopx-hoopR,hoopy-hoopR,hoopx+hoopR,hoopy+hoopR,
                                width=2, outline='orange')
        if self.teamTwo[0].onDefense and self.ballInHoop:
            self.canvas.create_oval(hoopx-ballR,hoopy-ballR,hoopx+ballR,hoopy+ballR,
                                    width=0,fill='orange')
        boardX = self.width-self.rightMargin-boardX
        self.canvas.create_line(boardX,boardY,boardX,boardY+self.backboardHeight,
                                width = 2, fill = 'grey')

    #splitting half-court into 25 boxes or 'spots'
    def setSpots(self):
        xSpotsOne = []
        xSpotsTwo = []

        gridCols = 10
        gridWidth = self.courtWidth / gridCols
        leftx = self.margin
        for col in range(gridCols):
            rightx = leftx + gridWidth
            xBounds = (math.ceil(leftx), math.floor(rightx))
            if col < gridCols/2: xSpotsOne.append(xBounds)
            else: xSpotsTwo.append(xBounds)
            leftx = rightx

        ySpots = []

        gridRows = 5
        gridHeight = self.courtHeight / gridRows
        topy = self.margin
        for row in range(gridRows):
            boty = topy + gridHeight
            yBounds = (topy + 1, boty)
            ySpots.append(yBounds)
            topy = boty

        self.passSpots(xSpotsOne, xSpotsTwo, ySpots)

    #passing on the spots to each Player 
    def passSpots(self, xOne, xTwo, y):
        for player in self.players:
            player.ySpots = y
            if player in self.teamOne:
                player.xSpots = xOne
            else:
                player.xSpots = xTwo

    #returns tuple of score
    def getScores(self):
        teamOneScore = teamTwoScore = 0
        for player in self.players:
            points = player.stats['PTS']
            if player in self.teamOne: teamOneScore += points
            else: teamTwoScore += points
        return (teamOneScore, teamTwoScore)

    #in the event of shot clock expiring
    def shotClockExpired(self):
        inboundingTeam = self.teamOne if self.teamOne[0].onDefense else self.teamTwo

        if self.ballBeingPassed:
            self.ballBeingPassed = False

        #finding who has the ball and taking it away
        for player in self.players:
            player.hasBall = False

        self.switchOffense()
        self.ballInHoop = True
        
        inboundingTeam[0].inbounding = True

    #draws each player, passes on canvas
    def drawPlayers(self):
        for player in self.players:
            player.drawSelf(self.canvas)

    #draws game clock and shot clock
    def drawClocks(self):
        (x0, y0) = (self.margin+self.courtWidth,0)
        (x1, y1) = (self.width,self.margin)
        self.canvas.create_rectangle(x0,y0,x1,y1,width=0,fill='white')
        (x, y) = (self.margin, self.height)
        #converting gameClock(seconds) to mm:ss
        gameMin = self.gameClock / 60
        gameSec = self.gameClock % 60
        self.timestamp = "[%02d:%02d]" % (gameMin, gameSec)
        shotClock = self.shotClockTime - self.shotClock #24 - elapsed time
        clocks = "Game clock [%02d:%02d]\nShot clock     [%02d]" % (gameMin, gameSec, shotClock)
        size = int(self.scale * 1.25)
        self.canvas.create_text((x1+x0)/2,(y1+y0)/2, font = ("Helvetica", size, 'normal'), text = clocks,fill='red')

    #draws the text for game events
    def drawDialogue(self):
        (x, y) = ((self.margin+self.courtWidth)*1.01, self.margin+self.courtHeight)
        size = int( self.scale * 0.9)
        self.canvas.create_text(x,y, anchor = SW, font = ("Helvetica", size), text = self.dialogue)

    #gets the box score
    def getBoxscore(self):
        statKeys = ["Name"] + self.players[0].sortedStatKeys
        boxscore = []

        boxscore.append([self.teamOneAttributes['teamName']] + [""]*11)
        for player in self.teamOne:
            statLine = [player.name]
            for stat in player.sortedStatKeys:
                statLine.append( stat + ":"+ str(player.stats[stat]))
            boxscore.append(statLine)
        boxscore.append([self.teamTwoAttributes['teamName']] + [""]*11)
        for player in self.teamTwo:
            statLine = [player.name]
            for stat in player.sortedStatKeys:
                statLine.append( stat + ":"+ str(player.stats[stat]))
            boxscore.append(statLine)

        boxscore = tabulate(boxscore,tablefmt="rst")
        return boxscore

    #in event of time expiring
    def timeExpires(self):
        oneName = self.teamOneAttributes['teamName']
        twoName = self.teamTwoAttributes['teamName']
        (oneScore, twoScore) = self.getScores()
        if oneScore > twoScore: winner = oneName
        elif twoScore > oneScore: winner = twoName
        else:
            self.dialogue += "\n\n OVERTIME - additional time.\n"
            self.spawnAroundCircle()
            self.gameOver = False
            self.stopClock = False
            self.startTime = time.time()
            self.gameClock = 0
            self.shotClockStartTime = time.time()
            self.shotClockTime = 24
            self.shotClock = 0
            self.endGameTime = self.overtimeTime
            time.sleep(1)
            return
        if not self.gameoverPrinted:
            self.dialogue += "\n GAME OVER."
            self.dialogue += "\nThe %s are the winners." % winner
            self.gameoverPrinted = True
        self.gameOver = True

    #draws the pause screen (box score)
    def drawPauseScreen(self):
        (x0,y0) = (self.margin, self.margin)
        (x1,y1) = (x0+self.courtWidth,y0+self.courtHeight)
        self.canvas.create_rectangle(x0,y0,x1,y1,fill='lightBlue')

        boxscore = self.getBoxscore()
        size = self.scale
        self.canvas.create_text((self.width-self.rightMargin)/2,self.height/2,
                                font=('Helvetica', size, 'normal'),text = boxscore)

    #draws the score
    def drawScore(self):
        (teamOneScore,teamTwoScore) = self.getScores()

        (onex,oney) = ((2*self.margin+self.courtWidth/2)/2, self.margin/2)
        (twox,twoy) = ((2*self.margin+3.0*self.courtWidth/2)/2,self.margin/2)
        oneName = self.teamOneAttributes['teamName']
        twoName = self.teamTwoAttributes['teamName']
        oneColor = self.teamOneAttributes['teamColor']
        twoColor = self.teamTwoAttributes['teamColor']
        size = int(self.scale*1.75)
        self.canvas.create_text(onex,oney,text="%s [%d]"%(oneName,teamOneScore),font=('Arial',size),fill=oneColor)
        self.canvas.create_text(twox,twoy,text="%s [%d]"%(twoName,teamTwoScore),font=('Arial',size),fill=twoColor)

    #draws start menu
    def drawMenu(self):
        self.canvas.create_rectangle(0,0,self.width,self.height,fill='black')

        #drawing photo
        self.canvas.create_image(self.width/2,self.height/2,image=self.photo)

        (x,y) = (self.width/2, 0)
        titleFont = int(self.scale * 2.4)
        self.canvas.create_text(x,y,text="Would the 1992 or 2012 Dream Team win?", fill='white',
                                anchor=N,justify=CENTER,font=("Helvetica", titleFont, 'underline'))
        with open('menuText.txt', 'r') as f: menuText = f.read()
        with open('rules.txt', 'r') as g: rules = g.read()
        (font1, font2) = (int(self.scale), int(self.scale*1.5))
        self.canvas.create_text(self.width/4,self.height/2,text=rules, fill='white',font=("Helvetica", font1, 'italic'))
        self.canvas.create_text(self.width*3/4,self.height/2, fill='white',text=menuText,font=("Helvetica", font2))

    #reset shot clock back to 24
    def resetShotClock(self):
        self.shotClockStartTime = time.time() - self.totalPausedTime

    #on each timer, each Player makes a decision
    def onTimerFired(self):
        if not (self.paused or self.gameOver or self.inMenu):
            currentTime = time.time()
            #also subtracting the totalPausedTime to get correct time
            self.gameClock = (currentTime - self.startTime - self.totalPausedTime)
            self.shotClock = (currentTime - self.shotClockStartTime - self.totalPausedTime)
            #checking shot clock
            if self.shotClock >= self.shotClockTime:
                self.dialogue += "\n%s BZZT. Shot clock expired!" % self.timestamp
                self.resetShotClock()
                self.shotClockExpired()
            #game time is up
            if self.gameClock >= self.endGameTime: self.timeExpires()
            #ball being passed
            if self.ballBeingPassed: self.passBall()

            for player in self.players:
                #user playing override
                if player is self.user and self.userPlaying:
                    if player.inbounding:
                        player.makeTransitionDecision()
                    player.moveToSpot()
                    continue
                #Players make decisions otherwise
                if player.inTransition or player.inbounding:
                    player.makeTransitionDecision()
                elif player.onDefense:
                    player.makeDefensiveDecision()
                elif player.onOffense:
                    offenseFreq = self.tempo / 100.0
                    if random.random() < offenseFreq:
                        player.makeOffensiveDecision()
                player.moveToSpot()

    #Control function in MVC
    def onMousePressed(self,event):
        self.user.spot = (event.x,event.y)

    #Control function in MVC
    def onKeyPressed(self, event):
        if self.inMenu:
            self.inMenu = False
            #exiting menu; get paused time
            self.pausedTime = time.time() - self.pauseStartTime
            self.totalPausedTime += self.pausedTime
        else:
            #reset the game!
            if (event.char == 'r'):
                self.initAnimation()
            #lock controls if game is over
            if not self.gameOver:
                #pause the game
                if (event.char == 'p'):
                    if self.paused:
                        self.pausedTime = time.time() - self.pauseStartTime
                        self.totalPausedTime += self.pausedTime
                    else:
                        self.pauseStartTime = time.time()
                    self.paused = not self.paused
                #shoot the ball
                elif (event.keysym == 'space'):
                    if self.user.hasBall and self.user.onOffense and self.userPlaying:
                        self.user.shoot()
                #pass to a teammate
                elif (event.char in "12345"):
                    position = int(event.char)
                    if position != self.user.position and self.user.hasBall:
                        if self.user.tryPassToTeammate(self.user.teammates[position-1]):
                            self.user = self.user.teammates[position-1]
                #toggle user override
                elif (event.char == 'u'):
                    self.userPlaying = not self.userPlaying
                    for player in self.teamOne:
                        if player.hasBall:
                            self.user = player
                            break
                elif (event.char == 'm'):
                    self.inMenu = True
                    self.pauseStartTime = time.time()

    #View function in MVC
    def redrawAll(self):
        self.canvas.delete(ALL)
        if self.inMenu:
            self.drawMenu()
        else:
            self.drawCourt()
            self.drawPlayers()
            self.drawHoops()
            self.drawScore()
            self.drawDialogue()
            self.drawClocks()
            self.setSpots()
            if self.ballBeingPassed:
                self.drawBall()
            if self.paused or self.gameOver:
                self.drawPauseScreen()

    #overriding to print game results after
    def run(self):
        super(Game, self).run()
        print("Printing game play-by-play...")
        print(self.dialogue)
        print()
        print("Printing box score...")
        print(self.getBoxscore())
        oneName = self.teamOneAttributes['teamName']
        twoName = self.teamTwoAttributes['teamName']
        (oneScore, twoScore) = self.getScores()
        print("FINAL SCORE: [%s: %d - %s: %d]" % (oneName,oneScore,twoName,twoScore))

game = Game(8) #change argument to fit resolution scale
game.run()