# coding=utf-8
from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)
from itertools import chain
import random
from math import floor
from umbs.user_settings import *

author = 'Benjamin Pichl'

doc = """
This app is intended to model a multi-uni resource allocation problem. It implements the University of Michigan Bidding 
System within the oTree framework. If you have any questions, comments, feature requests, or bug reports, 
please write me an eMail: benjamin.pichl@outlook.com.

If you intend to use this code for your own research purposes, please cite:

t.b.d.

"""


class Subsession(BaseSubsession):

    # METHOD: =================================================================================== #
    # THINGS TO DO BEFORE THE SESSION STARTS  =================================================== #
    # =========================================================================================== #
    def creating_session(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        indices = [j for j in range(1, Constants.nr_courses + 1)]
        players = self.get_players()

        # CREATE FORM TEMPLATES FOR DECISION.HTML  ============================================== #
        form_fields = ['bid_c' + str(n) for n in indices]

        for p in players:
            p.participant.vars['form_fields_plus_index'] = list(zip(indices, form_fields))
            p.participant.vars['player_bids'] = [None for n in indices]
            p.participant.vars['successful'] = [None for n in indices]

        # CREATE FORM TEMPLATES FOR CLEARING BID OUTPUT ========================================= #
        form_fields_clearing_bids = ['clearing_bid_c' + str(n) for n in indices]
        self.session.vars['form_fields_clearing_bids_plus_index'] = list(zip(indices, form_fields_clearing_bids))
        self.session.vars['clearing_bids'] = [None for i in indices]

        # ALLOCATE THE CORRECT VALUATIONS VECTOR TO PLAYER (DEPENDING ON TYPE) ================== #
        # AND GET OTHER PLAYERS' VALUATIONS AND TYPES TO DISPLAY IF DESIRED                       #
        type_names = ['Type ' + str(i) for i in range(1, Constants.nr_types + 1)]

        for p in players:
            p.participant.vars['valuations_others'] = []
            p.participant.vars['other_types_names'] = []
            for t in type_names:
                if p.role() == t:
                    p.participant.vars['valuations'] = Constants.valuations[type_names.index(t)]
                else:
                    if Constants.nr_types > 1:
                        p.participant.vars['valuations_others'].append(Constants.valuations[type_names.index(t)])
                        p.participant.vars['other_types_names'] = [t for t in type_names if p.role() != t]

    # METHOD: =================================================================================== #
    # PREPARE ADMIN REPORT ====================================================================== #
    # =========================================================================================== #
    def vars_for_admin_report(self):
        indices = [j for j in range(1, Constants.nr_courses + 1)]
        players = self.get_players()
        table_nr_tds_decisions = Constants.nr_courses + 2
        player_bids = [p.participant.vars['player_bids'] for p in players]
        last_player_per_group = [i[-1] for i in self.get_group_matrix()]
        player_valuations = [p.participant.vars['valuations'] for p in players]
        types = ['Type ' + str(i) for i in range(1, Constants.nr_types + 1)]
        valuations = [i for i in Constants.valuations]
        capacities = [i for i in Constants.capacities]
        decisions = zip(players, player_bids)
        successful = [p.participant.vars['successful'] for p in players]
        successful_with_id = zip(players, successful)
        valuations_all_types = zip(types, valuations)

        data_all = zip(players, player_valuations, player_bids, successful)

        return {
                'indices': indices,
                'players': players,
                'table_nr_tds_decisions': table_nr_tds_decisions,
                'player_bids': player_bids,
                'last_player_per_group': last_player_per_group,
                'capacities': capacities,
                'decisions': decisions,
                'successful': successful,
                'successful_with_id': successful_with_id,
                'valuations_all_types': valuations_all_types,

                'data_all': data_all
        }


class Group(BaseGroup):

    # DYNAMICALLY CREATE N FORM TEMPLATES FOR CLEARING BIDS  ==================================== #
    for j in range(1, Constants.nr_courses + 1):
        locals()['clearing_bid_c' + str(j)] = models.IntegerField(initial=0)
    del j

    # METHOD: =================================================================================== #
    # GET ALLOCATION (EXECUTED AFTER ALL PLAYERS SUBMITTED DECISION.HTML ======================== #
    # =========================================================================================== #
    def get_allocation(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        players = self.get_players()
        indices = [j for j in range(1, Constants.nr_courses + 1)]

        # COLLECT PREPARED_BID_LIST FROM ALL PLAYERS AND ORDER THEM IN ONE SINGLE LIST IN ======= #
        # DESCENDING ORDER OF BIDS. ALSO DELETE 0 BIDS.                                           #
        all_bids_with_0 = list(chain.from_iterable([p.participant.vars['prepared_bid_list'] for p in players]))
        all_bids = [i for i in all_bids_with_0 if i[0] >= 1]
        all_bids.sort(key=lambda sublist: sublist[0], reverse=True)

        # CREATE EMPTY LISTS FOR THE ALLOCATION PROCESS ========================================= #
        attendants = [[] for n in indices]
        schedules = [[] for p in players]

        # IMPLEMENTATION OF THE UMBS MECHANISM ================================================== #
        for b in all_bids:
            for n in indices:
                for p in players:
                    if b[2] == n and len(attendants[n - 1]) < Constants.capacities[n - 1]:
                        if b[1] == p.id_in_group and len(schedules[p.id_in_group - 1]) < Constants.s_len:
                            attendants[n - 1].append(b)
                            schedules[p.id_in_group - 1].append(b)

        # SAVE THE CLEARING BIDS TO SESSION VARS  =============================================== #
        # CLEARING BID IS THE LOWEST SUCCESSFUL BID TO ENROLL IN A COURSE. IF THERE ARE LESS      #
        # PARTICIPANTS THAN A COURSE'S CAPACITY, THE CLEARING BID FOR THIS COURSE IS SET TO 0.    #
        self.session.vars['clearing_bids'] = \
            [floor(i[-1][0]) if len(i) == Constants.capacities[attendants.index(i)] else 1 for i in attendants]

        # ASSIGN A SCHEDULE TO EACH SUBJECT AND CREATE A DUMMY VARIABLE FOR SUCCESSFUL BIDS IN == #
        # ORDER TO NICELY DISPLAY IT ON RESULTS.HTML.                                             #
        for p in players:
            p.participant.vars['schedule'] = schedules[p.id_in_group - 1]
            p.participant.vars['successful'] = \
                [True if i in p.participant.vars['schedule'] else False for i in p.participant.vars['prepared_bid_list']]

    # METHOD: =================================================================================== #
    # SET PAYOFFS =============================================================================== #
    # =========================================================================================== #
    def set_payoffs(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        players = self.get_players()
        indices = [j for j in range(1, Constants.nr_courses + 1)]

        # ADD EVERY VALUE OF A COURSE TO PAYOFF IF IT IS IN THE PLAYERS SCHEDULE ================ #
        for p in players:
            for i in p.participant.vars['schedule']:
                for n in indices:
                    if i[2] == n:
                        p.payoff += p.participant.vars['valuations'][n - 1]


class Player(BasePlayer):

    # METHOD: =================================================================================== #
    # DEFINE ROLES ACCORDING TO INPUT IN USER_SETTINGS.PY ======================================= #
    # =========================================================================================== #
    def role(self):
        # DESIGN TYPES ========================================================================== #
        all_ids = list(range(1, Constants.players_per_group + 1))
        nr_ids_per_type = int(Constants.players_per_group / Constants.nr_types)
        type_for_id = list(chain.from_iterable([[i] * nr_ids_per_type for i in range(1, Constants.nr_types + 1)]))
        type_matrix = [[i, j] for i, j in zip(all_ids, type_for_id)]

        for i in range(0, len(type_matrix)):
            if self.id_in_group == type_matrix[i][0]:
                return 'Type ' + str(type_matrix[i][1])

    # DYNAMICALLY CREATE N FORM TEMPLATES FOR BIDS ============================================== #
    for j in range(1, Constants.nr_courses + 1):
        locals()['bid_c' + str(j)] = models.IntegerField(label="", initial=0, min=0, max=Constants.endowment)
    del j

    # DYNAMICALLY CREATE N FORM TEMPLATES FOR SUCCESSFUL BIDS =================================== #
    for j in range(1, Constants.nr_courses + 1):
        locals()['successful_c' + str(j)] = models.BooleanField()
    del j

    # METHOD: =================================================================================== #
    # PREPARE BIDS IN ORDER TO IMPLEMENT TIE BREAKING =========================================== #
    # =========================================================================================== #
    def prepare_decisions(self):

        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        indices = [j for j in range(1, Constants.nr_courses + 1)]

        # GENERATE A RANDOM NUMBER FOR EACH COURSE FOR PLAYER P (FOR TIE-BREAKING) ============== #
        rand_nr = [random.random() for j in range(1, Constants.nr_courses + 1)]

        # MAKE A LIST OF BIDS + RANDOM NUMBERS ================================================== #
        self.participant.vars['prepared_bid_list'] = \
            [[sum(x)] for x in zip(self.participant.vars['player_bids'], rand_nr)]

        # APPEND PLAYER ID AND RESOURCE INDICES TO LIST ========================================= #
        for i in self.participant.vars['prepared_bid_list']:
            i.append(self.id_in_group)
        for i, j in zip(self.participant.vars['prepared_bid_list'], indices):
            i.append(j)
