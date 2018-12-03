# coding=utf-8
from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)
from itertools import chain
import random
from rsd.user_settings import *

author = 'Benjamin Pichl'

doc = """
This app is intended to model a multi-uni resource allocation problem. It implements the Random Serial Dictatorship 
Mechanism within the oTree framework. If you have any questions, comments, feature requests, or bug reports, 
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
        form_fields = ['pref_c' + str(j) for j in indices]

        for p in players:
            p.participant.vars['form_fields_plus_index'] = list(zip(indices, form_fields))
            p.participant.vars['player_prefs'] = [None for n in indices]
            p.participant.vars['successful'] = [None for n in indices]

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
        player_prefs = [p.participant.vars['player_prefs'] for p in players]
        last_player_per_group = [i[-1] for i in self.get_group_matrix()]
        player_valuations = [p.participant.vars['valuations'] for p in players]
        types = ['Type ' + str(i) for i in range(1, Constants.nr_types + 1)]
        valuations = [i for i in Constants.valuations]
        capacities = [i for i in Constants.capacities]
        decisions = zip(players, player_prefs)
        successful = [p.participant.vars['successful'] for p in players]
        successful_with_id = zip(players, successful)
        valuations_all_types = zip(types, valuations)

        data_all = zip(players, player_valuations, player_prefs, successful)

        return {
                'indices': indices,
                'players': players,
                'table_nr_tds_decisions': table_nr_tds_decisions,
                'player_prefs': player_prefs,
                'last_player_per_group': last_player_per_group,
                'capacities': capacities,
                'decisions': decisions,
                'successful': successful,
                'successful_with_id': successful_with_id,
                'valuations_all_types': valuations_all_types,

                'data_all': data_all
        }


class Group(BaseGroup):

    # METHOD: =================================================================================== #
    # GET ALLOCATION (EXECUTED AFTER ALL PLAYERS SUBMITTED DECISION.HTML ======================== #
    # =========================================================================================== #
    def get_allocation(self):
        # SHUFFLE PLAYER LIST IN ORDER TO OBTAIN RANDOM ORDERING OF PARTICIPANTS. ALSO, ========= #
        # WRITE THE NUMBER IN THE ORDERING TO A PLAYER VAR. FOR EACH SUBJECT.                     #
        players = self.get_players()
        random.shuffle(players)
        indices = [j for j in range(1, Constants.nr_courses + 1)]
        for p in players:
            p.position = players.index(p) + 1

        # TAKE THE LIST WITH ALL PLAYERS' PREFERENCES AND APPEND THEIR IDS AND THEIR PREFERENCES  #
        # AFTER THAT, SORT THE LIST IN A DESCENDING ORDER OF PREFERENCES                          #

        for p in players:
            for n in indices:
                p.participant.vars['player_prefs'][n - 1].append(p.id_in_group)
                p.participant.vars['player_prefs'][n - 1].append(n)

        all_prefs = list(chain.from_iterable([p.participant.vars['player_prefs'] for p in players]))
        all_prefs.sort(key=lambda sublist: sublist[0], reverse=False)

        # CREATE EMPTY LISTS FOR THE ALLOCATION PROCESS ========================================= #
        attendants = [[] for n in indices]
        schedules = [[] for p in players]

        # IMPLEMENTATION OF THE RSD MECHANISM =================================================== #
        for b in all_prefs:
            for n in indices:
                for p in players:
                    if b[2] == n and len(attendants[n-1]) < Constants.capacities[n-1]:
                        if b[1] == p.id_in_group and len(schedules[p.id_in_group - 1]) < Constants.s_len:
                            attendants[n-1].append(b)
                            schedules[p.id_in_group - 1].append(b)

        # AFTER ALL RESOURCES ARE ASSIGNED, GIVE EVERY SUBJECT THEIR SCHEDULES. ALSO, ASSIGN ==== #
        # A LIST OF SUCCESSFUL PREFS TO EACH SUBJECT, IN ORDER TO DISPLAY IT ON RESULTS.HTML.      #
        for p in players:
            p.participant.vars['schedule'] = schedules[p.id_in_group - 1]
            p.participant.vars['successful'] = \
                [True if i in p.participant.vars['schedule'] else False for i in p.participant.vars['player_prefs']]

    # METHOD: =================================================================================== #
    # SET PAYOFFS =============================================================================== #
    # =========================================================================================== #
    def set_payoffs(self):
        players = self.get_players()
        indices = [j for j in range(1, Constants.nr_courses + 1)]

        for p in players:
            for i in p.participant.vars['schedule']:
                for n in indices:
                    if i[2] == n:
                        p.payoff += p.participant.vars['valuations'][n - 1]


class Player(BasePlayer):

    # CREATE A FIELD FOR PLAYER POSITION IN THE ALLOCATION ====================================== #
    position = models.IntegerField()

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
        locals()['pref_c' + str(j)] = models.IntegerField()
    del j
