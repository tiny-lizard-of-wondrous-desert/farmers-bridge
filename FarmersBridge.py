import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
# import pickle
import datetime


class player(): #creates a new player
    def __init__(self, name, number = 0): #sets the player's name and number
        self.name = name
        self.number = number
        self.bids = []
        self.tricks = []
        self.score = 0
        
    def get_num(self): #retrieves the player's number
        return self.number
    
    def get_name(self): #checks the player's name
        return self.name
    
    def get_bids(self): #retrieves the player's guesses
        return self.bids
    
    def add_bid(self, bid): #adds a new guess to the player's guess list
        self.bids.append(bid)
    
    def get_tricks(self): #retrieves the player's tricks
        return self.tricks
    
    def add_trick(self, trick): #adds a new trick to the player's trick list
        self.tricks.append(trick)
    
    def get_score(self): #retrieves the player's score
        return self.score
    
    def update_score(self, above5 = False): #updates the player's score
        last_bid = self.bids[-1] #takes the most recent guess
        last_trick = self.tricks[-1] #takes the most recent trick
        old_score = self.score
        
        if last_bid == last_trick: #if the player got the right number of tricks
            if last_bid == 0: #if they did guess 0
                if above5 == False: #if they're below round 5
                    new_score = old_score + 10 #guessing 0 right is worth 10 points
                elif above5 == True: #if they're above round 5
                    new_score = old_score + 15 #guessing 0 right is worth 15 points
            else: #If they didn't guess 0-> the score goes up by 10 + the guess
                new_score = old_score + 10 + last_bid
        else: #if the player didn't get the right number of tricks ->
            #the score goes down by the number of tricks they were off of their guess
            new_score = old_score - abs(last_bid - last_trick)
        
        self.score = new_score #saving their new score
        
        
        
class game(): #creates a new game
    def __init__(self,  players = [], start_round = 1, end_round = 7, double_max = True, dealer = -1): #sets the players and rounds
        self.start_round = start_round
        self.end_round = end_round
        self.rounds = end_round - start_round
        self.current_round = start_round
        self.num_players = len(players)
        self.players = players
        self.direction = 'up'
        self.double_max = double_max
        self.current_dealer = players[dealer]
        self.round_count = start_round
        self.rounds_played = 0
        self.game_scores = pd.DataFrame()

        
        if self.double_max == False: #if the top round count is not doubled
            self.total_rounds = (self.rounds * 2) + 1 #sets the count for the loop
        elif self.double_max == True: #if the top round count is doubled
            self.total_rounds = (self.rounds * 2) + 2 #sets the count for the loop
        else:
            self.total_rounds  = (self.rounds * 2) + 1 #sets the count for the loop
           
        enough_cards = ((self.start_round > np.round(51/self.num_players)) | (self.end_round > np.round(51/self.num_players)))
        print(enough_cards, self.start_round, self.end_round, np.round(51/self.num_players))
        if enough_cards==True: #if the number of rounds is too many for the number of players, error out
            
            raise ValueError(f"{enough_cards}, {51/self.num_players}, Please input a smaller number of rounds, you won't have enough cards with the given number of players")
    
    def get_players(self):
        return self.players

    def switch_players(self):
        old_players = self.players #save the old list
        
        switching_player = old_players[0] #select the first player
        
        new_players = old_players[1:] #make the new list starting at the second player
        new_players.append(switching_player) #add the old first player to the end
        
        self.players = new_players #save the new list of players
    
    def playthrough(self): #making the game run through all of the rounds in one command
        
        rounds_left = self.total_rounds - self.rounds_played
        for i in range(rounds_left+1): #creates a while loop for the right number of rounds
            self.play_round() #plays the round
            print('''
            
            ''') #prints a gap between each round's prints
#             self.current_round += 1 #increases the round count in the while loop
            
    
    def enter_bids(self):
        self.current_guess_count = 0 #starts a total count for the round
        
        for i in range(self.num_players): #loops through the players for before the round is played
            current_player = self.players[i] #sets the current player
            
            if i == self.num_players - 1: #if it's the last player for the round
                cantcall = self.current_round-self.current_guess_count
                if cantcall >= 0:
                    print(f'You cannot call {self.current_round-self.current_guess_count}')#tells them what they can't call
                if cantcall <0:
                    print("You can call whatever you'd like")
                    
            bid = int(input(f'Enter bid for {current_player.get_name()}:  ')) #asks for an input from the players
            
            if i == self.num_players - 1: #if it's the last player for the round
                if bid == cantcall:
                    print("You can't call that, please reenter your score.")
                    bid = int(input(f'Reenter bid for {current_player.get_name()}:  ')) #asks for an input from the players
            
            if bid > self.current_round:
                print("Your bid is above the total number of tricks this round has, please guess lower.")
                bid = int(input(f'Enter bid for {current_player.get_name()}:  ')) #asks for an input from the players
            if bid < 0:
                print(f"Your bid is below zero, you can't win negative tricks, please guess between 0 and {self.current_round}.")
                bid = int(input(f'Enter bid for {current_player.get_name()}:  ')) #asks for an input from the players
            
            current_player.add_bid(bid) #adds the player's guess count to their guesses list
            self.current_guess_count += bid #adds the player's guess count to the total guess count
            
        
        amount_called_or_not_called = self.current_round - self.current_guess_count        
        if amount_called_or_not_called < 0: #if more tricks are called than there are to win
            sign = 'above the total number of tricks.'
        elif amount_called_or_not_called > 0: #if fewer tricks are called than there are to win
            sign = 'below the total number of tricks.'
        else:
            sign = 'hmmm' #set the sign to 'hmmm' because it shouldn't be this
            amount_called_or_not_called = 'breaking the call rules, silly.'
        
        print(' ')
        print(f'The current call total is {self.current_guess_count}. You are {abs(amount_called_or_not_called)} {sign}')
        
        return self
        
    def enter_tricks(self):
        
        self.trick_count = 0
        
        for i in range(self.num_players): #loops through the players for after the round is played
            current_player = self.players[i] #sets the current player
            trick = int(input(f'Enter trick for {current_player.get_name()}:  ')) #asks for an input from the players
                        
            if (trick > self.current_round) | (trick < 0):
                print(f"You can only win between 0 and {self.current_round} tricks, please reenter your tricks.")
                trick = int(input(f'Reenter trick for {current_player.get_name()}:  ')) #asks for an input from the players
            
            
            current_player.add_trick(trick) #adds the player's trick count to their tricks list
            self.trick_count += trick
            
        print(f"You've accounted for {self.trick_count} tricks")
        
        print(' ')
        if self.trick_count != self.current_round:
            print("PLEASE REENTER THE SCORES!!!")
        elif self.trick_count == self.current_round:
            print("You have the right number of tricks counted.")
        
        return self
    
    def check_errors(self):
        bid_lengths = []
        trick_lengths = []
        
        for player in self.players:
            bid_lengths.append(len(player.get_bids))
            trick_lengths.append(len(player.get_tricks))
        
        while bid_lengths != trick_lengths:
            min_bid_len = min(bid_lengths)
            min_trick_len = min(trick_lengths)
            bid_lengths = []
            trick_lengths = []
            for player in self.players:
                if len(player.get_bids) != min_bid_len:
                    player.get_bids = player.get_bids[-1]
                    
                if len(player.get_tricks) != min_trick_len:
                    player.get_tricks = player.get_tricks[-1]
                
                bid_lengths.append(len(player.get_bids))
                trick_lengths.append(len(player.get_tricks))
        
    def play_round(self): #plays the round   
        if self.current_round < self.start_round: #if there are 0 cards in the round (aka, it's done)
            self.game_scores.to_csv(f'./Game_Logs/{datetime.datetime.now()}.csv')
 
            name, score = self.update_ranks(returning = 'Top Player')
            return print(f'''
            There are no more rounds.
            
            {name} with {score} points!''')
            
        #as long as the round is above 0 (there are cards to play in the round)
        print(f'This is round number {self.current_round} on the way {self.direction}') #shows what round it is
        
        
#         self = self.check_errors() #checks to make sure we don't have extra trick/bid enters from erroring
        
        self = self.enter_bids() #adds the rounds bids
        
        self = self.enter_tricks() #adds the rounds tricks
        
        
        #MIGHT BE A BAD SPOT???
        self = self.fix_scores() #Provides a way to fix scores between rounds
        

        for i in range(self.num_players): #loops through the players for after the points are counted
            current_player = self.players[i] #sets the current player
            if self.current_round < 5: #if it's below round 5
                current_player.update_score(above5 = False) #updates the score
            elif self.current_round >= 5: #if it's not below round 5
                current_player.update_score(above5 = True) #updates the score

            self.game_scores.loc[self.round_count, current_player.get_name()] = current_player.get_score()
        
        #Sets up for the next round
        if self.direction == 'up': #if the rounds are going up
            if self.current_round >= self.end_round: #if they've passed the top
                self.direction = 'down' #change the direction
                if self.double_max == False:
                    self.current_round -= 1
                else:
                    self.double_max = False
            else:
                self.current_round += 1 #increase the round number
        else: #if they're going down already
            self.current_round -= 1 #decrease the round number
        
        self.round_count += 1
        self.rounds_played += 1
        
        print(' ')
        print(f'The next dealer is {self.players[0].get_name()}')
        
        self.switch_players()
        
        print('The current scores are:')
        self.update_ranks()
        
        
    def check_rules(self):
        print('Application rules:')
        print('You must input players in order from left to right. Dealer must be the last name.')
        print("You must input the number of rounds you'd like to play in each direction.")
        print('Ex: 7 means you will play 7 rounds from 1 card to 7 cards, then 7 more rounds from 7 cards to 1 card.')
        print("You must indicate whether you'd like to repeat the highest round.")
        print(' ')
        print('Game rules:')
        print("On round 'x', deal x cards to each player.")
        print('Flip the top card in the remaining stack over, the suit on that card is trump for the round.')
        print('Each player may look at their cards.')
        print('Each round, each player (starting to the left of the dealer) will guess how many tricks they will win in that round')
        print('The dealer may not call a number that will bring the total called to the round number.')
        print('Ex: if the total call is at 2 and it is the 3rd round, the dealer may not call 1.')
        print('You may not change your call after the next person has called. (House rules determine whether you may after your initial call before the next player calls.)')
        print('Once everyone has called, the player to the left of the dealer leads.')
        print('You must follow suit, if you do not have the suit played you may trump it or throw off')
        print('This is not a team game, each player has their own score.')
        print('Scoring is calculated automatically, updated scores will be displayed each round.')
        print('If you bid the same number as the tricks you get in the round, you will get 10 points plus your bid.')
        print('If you bid 0 and it is round 5+ (you have at least 5 cards in your hand), you will recieve 15 points')
        print("If your bid and number of tricks aren't equal, you will lose as many points as you are off of your bid.")
        print("You'll lose points for being over and under your bid")
        print('Ace is high.')
        print('Unlike euchre, the jack of trump is not high and jacks of the same color but other suit are not trump.')
        print('You may not table talk.')
        
    def check_score(self):
        for player in self.players:
            print(f'{player.get_name()} is at {player.get_score()}')
           
    def get_game_scores(self):
        return self.game_scores
        
    def get_players(self):
        return self.players
    
    def update_ranks(self, returning = 'Print'):
        score_dict = {}
        for player in self.players:
            score_dict[player.get_name()] = player.get_score()
            
        sorted_scores = sorted(score_dict.items(), key=lambda x: x[1], reverse = True)
        
        if returning == 'Print':
            for i in sorted_scores:
                print(i[0], i[1])
        elif returning == 'Top Player':
            top_player, top_score = sorted_scores[0][0], sorted_scores[0][1]
            top_players = [top_player]
            for i in range(self.num_players):
                other_player, other_score = sorted_scores[i][0], sorted_scores[i][1]
                if other_player != top_player:
                    if other_score == top_score:
                        top_players.append(other_player)

            
            topplayers = ''
            if len(top_players) != 1:
                for i in range(len(top_players)):
                    if (i != 0):
                        topplayers += ', '
                    if i == (self.num_players - 1):
                        topplayers += 'and '
                    topplayers += top_players[i]  
                topplayers += ' are the winners'
                
            elif len(top_players) == 1:
                topplayers = top_player
                topplayers += ' is the winner'

            return topplayers, top_score
        else:
            raise ValueError('How am I supposed to update this?')
            
    def fix_scores(self):
        
        fixing = input("Would you like to change the scores? (Please input 'Yes' or 'No'):")
        
        if fixing in ('No', 'NO', 'no'):
            return self
        if fixing in ('Yes', 'YES', 'yes', 'YEs', 'YeS', 'yES'):
            
            self.enter_bids()
            
            self.enter_tricks()
            
            self.fix_scores()
            
            return self
            
        else:
            print("I'm not sure what you want me to do, please input 'No' or 'Yes'.")
            self.fix_scores()
            return self
        
        
        
        
        
# df = pd.DataFrame(columns=['Player1', 'Player2'])

# df.to_csv(f'./Game_Logs/{datetime.datetime.now()}.csv')
# # pd.read_csv('2022-12-19 14:42:05.902090.csv')



def create_game(player_names, start_round = 1, end_round = 7, double_max = True, dealer = 0):
    players = []
    for i in range(len(player_names)):
        playeri = player(player_names[i], i)
        players.append(playeri)
    return game(players = players, start_round = start_round, end_round = end_round, double_max = double_max, dealer = dealer)



