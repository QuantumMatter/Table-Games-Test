from math import ceil

# import table_games
from table_games.common.cards import *
from table_games.blackjack.blackjack import Blackjack, BlackjackState, best_total
from table_games.blackjack.basic import BasicPolicy

# from cards import CSuit, CValue, Card, Deck
# from blackjack import Blackjack, BlackjackState, best_total
# from basic import BasicPolicy

# 6 spots, perfect basic strategy, $10/spot
d = [
    # Burn Card
    # 'D5',

    # Round 1 - Hit, Stand, & Double against 6
    'CA', 'D4', 'H7', 'H6', 'CJ', 'DT',     'S6',
    'D5', 'D2', 'CT', 'H5', 'CJ', 'D2',     'ST',

    'H4',   # Spot 1 Doubles, stands on soft 20
    'CT',   # Spot 2 Hits, stands on hard 16
            # Spot 3 Stands, on hard 17
    'C8',   # Spot 4 Doubles, stands on hard 19
            # Spot 5 Stands on hard 20
            # Spot 6 Stands, on hard 12

    'D8',   # Dealer draws to hard 24, busts

    # P1: $20, P2: $10, P3: $10, P4: $20, P5: $10, P6: $10
    
    # Round 2 - Hit, Stand, Double, Split against 8
    'C4', 'DK', 'S5', 'H8', 'S8', 'H7',     'C8',
    'CJ', 'DK', 'C5', 'H7', 'DQ', 'D7',     'HQ',

    'H8',   # Spot 1 hits, busts with hard 22
            # Spot 2 stands, on hard 20
    'CQ',   # Spot 3 doubles, stands on hard 20
    'C7',   # Spot 4 hits, busts with hard 22
            # Spot 5 stands, on hard 18
    'D3',   # Spot 6 hits, stands on hard 17

    # P1: $10, P2: $20, P3: $30, P4: $10, P5: $10, P6: $0

    # Round 3 - Blackjack, Hit, Double, Split, Stand, Push against 2 -> 21
    'CA', 'H4', 'S6', 'C3', 'HQ', 'D7',     'C2',
    'CK', 'D8', 'D5', 'D3', 'S3', 'H2',     'DT',

            # Spot 1 has a blackjack
    'CJ',   # Spot 2 hits, busts with hard 22
    'HJ',   # Spot 3 doubles, stands on hard 21
            # Spot 4 splits
    'H7',   # Spot 4(a) is dealt 7, has hard 10
    'C8',   # Spot 4(a) doubles; stands on hard 18
    'H9',   # Spot 4(b) is dealt 9, has hard 12
    'H3',   # Spot 4(b) hits, stands on hard 15
            # Spot 5 stands on hard 13
    'C2',   # Spot 6 hits; has 11
    'CT',   # Spot 6 hits; has 21

    'D9',   # Dealer draws to 21

    # P1: $25, P2: $10, P3: $30, P4: $-20, P5: $0, P6: $0

    # Round 4 - Splitting Aces against a Ten
    'CA', 'CT', 'CA', 'SA', 'H8', 'D7',     'HT',
    'DA', 'HT', 'HA', 'CA', 'D3', 'H7',     'DT',

            # Spot 1 splits aces
    'D2',   # Spot 1(a) is dealt 2, must stand on soft 13
    'H9',   # Spot 1(b) is dealt 9, must stand on hard 20
            # Spot 2 stands on hard 20
            # Spot 3 splits aces
    'HA',   # Spot 3(a) is dealt an Ace, and SPLITS again
    'CT',   # Spot 3(a)(a) is dealt 10, stands on soft 21
    'C5',   # Spot 3(a)(b) is dealt  5, stands on soft 16
    'H8',   # Spot 3(b)    is dealt  8, stands on soft 19
            # Spot 4 splits aces
    'S7',   # Spot 4(a)    is dealt  7, stands on soft 18
    'DT',   # Spot 4(b)    is dealt 10, stands on soft 21
    'H6',   # Spot 5 DOUBLES, has soft 17
    'S3',   # Spot 6 HITS, stands on hard 17

    # P1: $15, P2: $10, P3: $20, P4: $-20, P5: $-20, P6: $-10

    'DK'
]

pen = len(d) / 52
deck_count = ceil(pen)

for _ in range(len(d), deck_count*52):
    d.append('DK')

expectations = [
    [0,  0,  0,  0,  0,  0],
    [20, 10, 10, 20, 10, 10],
    [10, 20, 30, 10, 10, 0],
    [25, 10, 30, -20, 0, 0],
    [15, 10, 20, -20, -20, -10]
]

suit_map = {
    'C': CSuit.CLUBS.value,
    'S': CSuit.SPADES.value,
    'H': CSuit.HEARTS.value,
    'D': CSuit.DIAMONDS.value
}
value_map = {
    'A': CValue.ACE.value,
    'K': CValue.KING.value,
    'Q': CValue.QUEEN.value,
    'J': CValue.JACK.value,
    'T': CValue.TEN.value,
    '9': CValue.NINE.value,
    '8': CValue.EIGHT.value,
    '7': CValue.SEVEN.value,
    '6': CValue.SIX.value,
    '5': CValue.FIVE.value,
    '4': CValue.FOUR.value,
    '3': CValue.THREE.value,
    '2': CValue.TWO.value
}

def do_test():
    assert 4 == 4

def test_basic_strategy():

    cards = list(map(lambda short: Card(suit_map[short[0]], value_map[short[1]]), d))
    deck = Deck(cards)

    game = Blackjack(deck_count, True, pen, 1, 100)
    for _ in range(6):
        game.add_player(BasicPolicy())
    game._deck = deck

    round_idx = 0
    while True:
        if round_idx >= len(expectations):
            break

        if game._state == BlackjackState.PREBETTING:
            expectation = expectations[round_idx]
            for player_idx, (player_expected, (playerPolicy, playerState)) in enumerate(zip(expectation, game._players)):
                assert player_expected == playerState._bank
                if player_expected != playerState._bank:
                    print(f'Round { round_idx + 1 } failed! Player { player_idx + 1 } has ${ playerState._bank }, but should have ${ player_expected }')
                    # exit()
            print(f'Before Round { round_idx+1 } is OK')

        elif game._state == BlackjackState.ACTION:
            print(f'Dealer has { game._dealer }')
            for p_idx, (p_policy, p_state) in enumerate(game._players):
                for s_idx, spot in enumerate(p_state._spots):
                    print(f'Player { p_idx+1 }.{ s_idx+1 } has { spot._cards }')

        elif game._state == BlackjackState.CLEANUP:
            round_idx += 1
            print(f'Dealer has { game._dealer }')
            for p_idx, (p_policy, p_state) in enumerate(game._players):
                for s_idx, spot in enumerate(p_state._spots):
                    print(f'Player { p_idx+1 }.{ s_idx+1 } has { spot._cards }')

        game.next()

    print('Pass!')
