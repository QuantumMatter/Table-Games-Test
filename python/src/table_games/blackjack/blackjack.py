from enum import Enum
from copy import deepcopy
from typing import List, Tuple

from table_games.common import CValue, Card, Deck

MAX_PLAYERS = 6

class SpotState:
    
    def __init__(self):
        self._bet = 0
        self._cards: List[Card] = []
        self._split = False
        self._insured = False

    def dealt(self, card: Card) -> None:
        self._cards.append(card)


class SpotAction: pass
class SpotStandAction(SpotAction): pass
class SpotHitAction(SpotAction): pass
class SpotSplitAction(SpotAction): pass
class SpotDoubleAction(SpotAction): pass


class SpotPolicy:

    @classmethod
    def Action(cls, spot: SpotState, table, submit) -> None:
        raise NotImplementedError()


class PlayerState:
    
    def __init__(self) -> None:
        self._spots = [SpotState()]
        self._bank = 0


class PlayerAction: pass
class PlayerSpreadAction(PlayerAction):
    def __init__(self, spots) -> None:
        super().__init__()
        self.spots = spots

class PlayerPolicy:

    @classmethod
    def PrebetAction(cls, player: PlayerState, submit):
        raise NotImplementedError()
    
    @classmethod
    def Bet(cls, player: PlayerState, submit):
        raise NotImplementedError()
    
    @classmethod
    def InsuranceAction(cls, player: PlayerState) -> bool:
        raise NotImplementedError()
    
    @classmethod
    def Action(cls, player: PlayerState, spot: SpotState, up_card: Card, submit):
        raise NotImplementedError()
    

class Ploppy(PlayerPolicy):

    BET = 10
    SPOTS = [
        SpotPolicy()
    ]

    @classmethod
    def PrebetAction(cls, player: PlayerState, submit):
        return PlayerSpreadAction(1)
    
    @classmethod
    def Bet(cls, player: PlayerState, submit):
        submit(10)

    @classmethod
    def Action(cls, player: PlayerState, spot: SpotState, up_card: Card, submit):
        cls.SPOTS[0].Action(spot, None, submit)


class BlackjackState(Enum):

    PREBETTING = 1  # Player is allowed to spread to different spots and change their bankroll
    BETTING = 2     # Player determines what their bet is for the upcoming hand
    DEALING = 3     # The dealer distributes cards to each of the spots for all of the players
    ACTION = 4      # Players determine what actions they would like to take for each of their spots
    RESULTS = 5     # The dealer plays their hand and determines winners, losers, and payouts
    CLEANUP = 6     # The state of the players are reset


def hard_total(cards: List[Card]):
    return sum(map(lambda card: min(card._value, 10), cards))

def soft_total(cards: List[Card]):
    total = hard_total(cards)

    has_ace = False
    for card in cards:
        if card._value == 1:
            has_ace = True
            break

    if has_ace:
        total += 10
    
    return total

def best_total(cards, against=17):
    hard = hard_total(cards)
    soft = soft_total(cards)
    if soft > 21: return hard
    if hard > 21: return hard
    if hard > against: return hard
    if soft > against: return soft
    if soft > 21: return hard
    return hard if (hard >= 17) else soft

def is_blackjack(cards):
    if len(cards) != 2: return False
    if soft_total(cards) != 21: return False
    return True


class Wrapper:
    def __init__(self, value) -> None:
        self.value = value


class Blackjack:

    def __init__(self, deck_count: int, h17: bool, pen: float, tmin: int, tmax: int, das = True, spc = 4, rsa = True, bj = 1.5) -> None:
        """
        Arguments:
            deck_count: The number of decks in the shoe
            h17: True of the dealer must hit a soft 17 (so they must always have a hard 17)
            pen: The penetration of the shoe, measured in the number of decks remaining before the cut card
            tmin: The minimum table bet
            tmax: The maximum table bet
            das: True if the player is allowed to Double After Splitting
            spc: The number of hands a player is allowed to split to
            rsa: True if the player is allowed to re-split aces
            bj: The pay rate of getting a blackjack
        """
        
        self._deck_count = deck_count
        self._h17 = h17
        self._pen = pen
        self._tmin = tmin
        self._tmax = tmax
        self._das = das
        self._spc = spc
        self._rsa = rsa
        self._bj = bj

        self._players: List[Tuple[PlayerPolicy, PlayerState]] = []
        self._deck = Deck.Standard()
        for _ in range(self._deck_count - 1):
            self._deck += Deck.Standard()
        self._deck.shuffle()
        self._deck.draw()

        self._state = BlackjackState.PREBETTING
        self._dealer: List[Card] = []

    def add_player(self, player: PlayerPolicy):
        if len(self._players) >= MAX_PLAYERS:
            return False
        else:
            self._players.append((player, PlayerState()))
            return True
        
    def next(self) -> bool:
        if len(self._players) <= 0: return False

        if self._state == BlackjackState.PREBETTING:
            for playerPolicy, playerState in self._players:
                
                def submit(action: PlayerAction):
                    if type(action) is PlayerSpreadAction:
                        desired_spots = action.spots

                        print(f"Desired spots: { desired_spots }")

                        if desired_spots > (MAX_PLAYERS // len(self._players)):
                            return False
                        else:
                            playerState._spots = [SpotState() for _ in range(desired_spots)]
                            return True
                    else:
                        return False
                    
                playerPolicy.PrebetAction(deepcopy(playerState), submit)
            
            self._state = BlackjackState.BETTING

        elif self._state == BlackjackState.BETTING:
            for playerPolicy, playerState in self._players:
                
                def submit(bet):
                    if bet < self._tmin: return False
                    if bet > self._tmax: return False

                    for spot in playerState._spots:
                        spot._bet = bet
                        playerState._bank -= bet

                    return True
                    
                playerPolicy.Bet(deepcopy(playerState), submit)

            self._state = BlackjackState.DEALING

        elif self._state == BlackjackState.DEALING:
            for playerPolicy, playerState in self._players:
                for spot in playerState._spots:
                    spot.dealt(self._deck.draw())

            self._dealer.append(self._deck.draw())

            for playerPolicy, playerState in self._players:
                for spot in playerState._spots:
                    spot.dealt(self._deck.draw())
                    
            self._dealer.append(self._deck.draw())

            if self._dealer[0]._value == 1:
                # Insurance
                for playerPolicy, playerState in self._players:
                    takes_insurance = playerPolicy.InsuranceAction(deepcopy(playerState))
                    if takes_insurance:
                        for spot in playerState._spots:
                            playerState._bank -= 0.5 * spot._bet
                            spot._insured = True

            if is_blackjack(self._dealer):
                print('Dealer has a blackjack!')
                for playerPolicy, playerState in self._players:
                    for spot in playerState._spots:
                        if spot._insured:
                            playerState._bank += (3/2) * spot._bet

                self._state = BlackjackState.CLEANUP
            else:
                self._state = BlackjackState.ACTION

        elif self._state == BlackjackState.ACTION:
            for playerPolicy, playerState in self._players:
                spot_idx = Wrapper(0)
                while spot_idx.value < len(playerState._spots):
                    spot = playerState._spots[spot_idx.value]
                    if len(spot._cards) == 1:
                        spot.dealt(self._deck.draw())

                        split_aces = spot._cards[0]._value == CValue.ACE.value
                        dealt_second_ace = spot._cards[1]._value == CValue.ACE.value
                        has_action = (not split_aces) or dealt_second_ace

                        if not has_action:
                            spot_idx.value += 1
                            continue
                    elif len(spot._cards) == 2 and soft_total(spot._cards) == 21:
                        print(f"{ spot._cards }")
                        print("Blackjack!")
                        spot_idx.value += 1
                        continue


                    done = Wrapper(False)
                    
                    while not done.value:

                        def submit(action: SpotAction) -> bool:
                            if type(action) is SpotStandAction:
                                print(f'STAND on { spot._cards } vs { self._dealer[0] }')
                                done.value = True
                                return True
                            elif type(action) is SpotHitAction:
                                print(f'HIT on { spot._cards } vs { self._dealer[0] }')
                                spot.dealt(self._deck.draw())
                                if hard_total(spot._cards) > 21:
                                    print(f"You drew a { spot._cards[-1] } and busted!")
                                    done.value = True
                                return True
                            elif type(action) is SpotDoubleAction:
                                if len(spot._cards) != 2: return False
                                if spot._split == True and self._das == False: return False

                                print(f'DOUBLE on { spot._cards } vs { self._dealer[0] }')
                                spot.dealt(self._deck.draw())
                                print(f"You drew a { spot._cards[-1] }!")
                                playerState._bank -= spot._bet
                                spot._bet *= 2
                                
                                done.value = True
                                return True
                            elif type(action) is SpotSplitAction:
                                if len(spot._cards) != 2: return False
                                a_val = min(10, spot._cards[0]._value)
                                b_val = min(10, spot._cards[1]._value)
                                if a_val != b_val: return False

                                print(f'SPLIT on { spot._cards } vs { self._dealer[0] }')
                                new_spot = SpotState()
                                new_spot._bet = spot._bet
                                playerState._bank -= new_spot._bet
                                new_spot.dealt(spot._cards[1])
                                new_spot._split = True
                                spot._split = True
                                playerState._spots.insert(spot_idx.value+1, new_spot)
                                spot._cards.remove(spot._cards[1])
                                spot_idx.value -= 1
                                done.value = True
                                return True
                            
                        playerPolicy.Action(playerState, spot, self._dealer[0], submit)
                    
                    spot_idx.value += 1

            self._state = BlackjackState.RESULTS

        elif self._state == BlackjackState.RESULTS:
            
            while True:
                hard = hard_total(self._dealer)
                soft = soft_total(self._dealer)

                if hard >= 17:
                    break
                elif soft <= 21 and soft >= 18:
                    break
                else:
                    self._dealer.append(self._deck.draw())

            dealer_total = best_total(self._dealer)

            for playerPolicy, playerState in self._players:
                for spot in playerState._spots:
                    spot_total = best_total(spot._cards, dealer_total)
                    if (not spot._split) and (len(spot._cards) == 2) and (soft_total(spot._cards) == 21):
                        playerState._bank += (1 + self._bj) * spot._bet
                    elif spot_total > 21:           # Player busted
                        continue
                    elif dealer_total > 21:         # Dealer busted
                        playerState._bank += 2 * spot._bet
                    elif spot_total == dealer_total:# Push
                        playerState._bank += spot._bet
                    elif spot_total < dealer_total: # Lost
                        continue
                    elif spot_total > dealer_total:
                        playerState._bank += 2 * spot._bet
                    else:
                        raise Exception()

            self._state = BlackjackState.CLEANUP

        elif self._state == BlackjackState.CLEANUP:
            self._dealer.clear()
            for playerPolicy, playerState in self._players:
                for spot in playerState._spots:
                    spot._bet = 0
                    spot._cards.clear()
                playerState._spots.clear()

            if (self._deck_count - self._pen) * 52 > len(self._deck):
                print("Shuffling...")
                self._deck = Deck.Standard()
                for _ in range(self._deck_count - 1):
                    self._deck += Deck.Standard()
                self._deck.shuffle()
                self._deck.draw()

            self._state = BlackjackState.PREBETTING

        return True


class CLIPlayer(PlayerPolicy):

    def __init__(self, name) -> None:
        super().__init__()
        self.name = name

    @classmethod
    def PrebetAction(cls, player: PlayerState, submit):
        while True:
            cli_bet = input("Please input the number of spots you would like to spread to: ")
            cli_bet = int(cli_bet)
            if submit(PlayerSpreadAction(cli_bet)):
                break
            else:
                print("Invalid entry. Please enter a different value")

    @classmethod
    def Bet(cls, player: PlayerState, submit):
        while True:
            cli_bet = input("Please input the amount you would like to bet for this hand: ")
            cli_bet = int(cli_bet)
            if submit(cli_bet):
                break
            else:
                print("Invalid entry. Please enter a different value")

    @classmethod
    def InsuranceAction(cls, player: PlayerState) -> bool:
        while True:
            cli_bet = input("Would you like insurance? [y/n]: ")
            if cli_bet == "y":
                return True
            elif cli_bet == "n":
                return False
            else:
                print("Invalid entry. Please enter a different value")

    @classmethod
    def Action(cls, player: PlayerState, spot: SpotState, up_card: Card, submit):
        while True:
            print(f'Hand: { spot._cards }')
            cli_bet = input("Select action (s: Stand, h: Hit, d: Double, v: Split): ")
            if cli_bet == "s": 
                if submit(SpotStandAction()): break
            elif cli_bet == "h":
                if submit(SpotHitAction()): break
            elif cli_bet == "d":
                if submit(SpotDoubleAction()): break
            elif cli_bet == "v":
                if submit(SpotSplitAction()): break
            else:
                print("Invalid entry. Please enter a different value")
    

if __name__ == "__main__":
    game = Blackjack(2, True, 1, 10, 300, True, 4, False, 3/2)
    player = CLIPlayer("David")
    game.add_player(player)

    while True:
        if game._state == BlackjackState.PREBETTING:
            print(f"You have ${ game._players[0][1]._bank }")
        elif game._state == BlackjackState.ACTION:
            print(f"The dealer is showing { game._dealer[0] }")
        elif game._state == BlackjackState.CLEANUP:
            print(f"The dealer drew to { game._dealer }")

            dealer_total = best_total(game._dealer)
            for playerPolicy, playerState in game._players:
                for spot in playerState._spots:
                    spot_total = best_total(spot._cards, dealer_total-1)
                    if (not spot._split) and (len(spot._cards) == 2) and (soft_total(spot._cards) == 21):
                        print(f"{ spot._cards } wins ${ (1 + game._bj) * spot._bet }")
                    elif spot_total > 21:             # Player busted
                        print(f"{ spot._cards } loses ${ spot._bet }")
                    elif dealer_total > 21:         # Dealer busted
                        print(f"{ spot._cards } wins ${ spot._bet }")
                    elif spot_total == dealer_total:# Push
                        print(f"{ spot._cards } pushes")
                    elif spot_total < dealer_total: # Lost
                        print(f"{ spot._cards } loses ${ spot._bet }")
                    elif spot_total > dealer_total:
                        print(f"{ spot._cards } wins ${ spot._bet }")
                    else:
                        raise Exception()


        if not game.next():
            break
