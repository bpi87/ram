# coding=utf-8
from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
)
from itertools import chain
import random
from math import floor
from da.user_settings import *

author = 'Benjamin Pichl'

doc = """
This app is intended to model a school choice problem. It implements the Student Proposing Deferred Acceptance 
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
            p.participant.vars['successful'] = [False for n in indices]

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

        # ALLOCATE THE CORRECT PRIORITIES VECTOR TO PLAYER (DEPENDING ON ID) ==================== #
        for p in players:
            p.participant.vars['priorities'] = []
            for i in Constants.priorities:
                p.participant.vars['priorities'].extend([(i.index(j) + 1) for j in i if j == p.id_in_group])

    # METHOD: =================================================================================== #
    # PREPARE ADMIN REPORT ====================================================================== #
    # =========================================================================================== #
    def vars_for_admin_report(self):
        indices = [j for j in range(1, Constants.nr_courses + 1)]
        players = self.get_players()
        table_nr_tds_decisions = Constants.nr_courses + 2
        table_nr_tds_priorities = Constants.nr_courses + 1
        player_prefs = [p.participant.vars['player_prefs'] for p in players]
        last_player_per_group = [i[-1] for i in self.get_group_matrix()]
        player_valuations = [p.participant.vars['valuations'] for p in players]
        player_priorities = [p.participant.vars['priorities'] for p in players]
        types = ['Type ' + str(i) for i in range(1, Constants.nr_types + 1)]
        valuations = [i for i in Constants.valuations]
        capacities = [i for i in Constants.capacities]
        decisions = zip(players, player_prefs)
        successful = [p.participant.vars['successful'] for p in players]
        successful_with_id = zip(players, successful)
        valuations_all_types = zip(types, valuations)
        priorities_all_players = zip(players, player_priorities)

        data_all = zip(players, player_valuations, player_prefs, successful)

        return {
                'indices': indices,
                'players': players,
                'table_nr_tds_decisions': table_nr_tds_decisions,
                'table_nr_tds_priorities': table_nr_tds_priorities,
                'player_prefs': player_prefs,
                'last_player_per_group': last_player_per_group,
                'player_priorities': player_priorities,
                'capacities': capacities,
                'decisions': decisions,
                'successful': successful,
                'successful_with_id': successful_with_id,
                'valuations_all_types': valuations_all_types,
                'priorities_all_players': priorities_all_players,

                'data_all': data_all
        }


class Group(BaseGroup):

    # METHOD: =================================================================================== #
    # GET ALLOCATION (EXECUTED AFTER ALL PLAYERS SUBMITTED DECISION.HTML ======================== #
    # =========================================================================================== #
    def get_allocation(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        players = self.get_players()
        indices = [j for j in range(1, Constants.nr_courses + 1)]

        # COLLECT PREPARED_LIST FROM ALL PLAYERS AND ORDER THEM IN ONE SINGLE LIST IN =========== #
        # DESCENDING ORDER OF PREFS.                                                              #
        all_prefs = list(chain.from_iterable([p.participant.vars['prepared_list'] for p in players]))
        all_prefs.sort(key=lambda sublist: sublist[0], reverse=False)

        # CREATE EMPTY LISTS FOR THE ALLOCATION PROCESS ========================================= #
        attendants = [[] for n in indices]
        player_resource = [[] for p in players]

        # CREATE COUNTER VARIABLE FOR THE WHILE LOOP (FIRST PASS IS DIFFERENT TO THE FOLLOWING == #
        # PASSES).                                                                                #
        pass_i = 0

        # CREATE A LIST TO ITERATE OVER DURING THE ALLOCATION PROCESS. IN THE BEGINNING, THIS === #
        # LIST CONTAINS JUST A DUMMY ITEM IN ORDER TO GET OVER THE FIRST PASS OF THE LOOP.        #
        iterlist = [0]

        # IMPLEMENTATION OF THE DA MECHANISM ==================================================== #
        while len(iterlist) > 0:
            if pass_i == 0:

                # TENTATIVELY ASSIGN ALL DESIRED COURSES ======================================== #
                for b in all_prefs:
                    for n in indices:
                        if b[0] == 1 and b[3] == n:
                            attendants[n - 1].append(b)

                # REMOVE THOSE ITEMS FROM ALL_PREFS. THE REMAINDER OF ALL_PREFS NOW CONTAINS ==== #
                # ALL REMAINING PREFS FOR THE ITERATION PROCESS.                                  #
                all_prefs = [b for b in all_prefs if b[0] > 1]

                # UPDATE COUNTER ================================================================ #
                pass_i += 1

                # INITIALIZE A LIST FOR PREFS THAT WERE CONSIDERED DURING THE PROCESS, BUT WERE = #
                # THEN DROPPED AGAIN.                                                             #
                droplist = []

            # ITERATION PROCESS AFTER INITIALLY ASSIGNING TOP CHOICE RESOURCES IN PASS 0 ======== #
            else:
                # SORT LIST OF TENTATIVE ATTENDANTS IN THE PREVIOUS PASS AND INSPECT IF A ======= #
                # RESOURCE TENTATIVELY HOLDS MORE SUBJECTS THAN ITS CAPACITY. IF THIS             #
                # IS THE CASE, ...                                                                #
                for n in indices:
                    attendants[n - 1].sort(key=lambda sublist: sublist[1], reverse=False)

                    if len(attendants[n - 1]) > Constants.capacities[n - 1]:
                        # ... APPEND THOSE BIDS TO THE DROPLIST AND ... ========================= #
                        for b in attendants[n - 1]:
                            if attendants[n - 1].index(b) > Constants.capacities[n - 1] - 1:
                                droplist.append(b)

                        # ... REMOVE THE PREFS THAT EXCEED OVERDEMAND FROM THE COURSE. ========== #
                        attendants[n - 1] = attendants[n - 1][0:Constants.capacities[n - 1]]

                # NEXT, WE UPDATE ITERLIST FOR THIS ROUND, SUCH THAT IT CONTAINS ALL ITEMS THAT = #
                # A) HAVE NOT ALREADY BEEN ASSIGNED TO A SUBJECT, AND                             #
                # B) HAVE NOT BEEN DROPPED IN THIS OR A PREVIOUS ROUND.                           #
                all_attendants_flat = list(chain.from_iterable(attendants))
                iterlist = [b for b in all_prefs if b[0] > 1 and b not in droplist and b not in all_attendants_flat]
                iterlist.sort(key=lambda sublist: sublist[0], reverse=False)

                # CREATE VARIABLE TO STORE PLAYERS THAT HAVE ALREADY BEEN ALLOCATED ============= #
                allocated_players = []
                for p in players:
                    allocated_players.append(len([i for i in all_attendants_flat if i[2] == p.id_in_group]))

                for p in players:
                    if allocated_players[p.id_in_group - 1] == 1:
                        iterlist = [i for i in iterlist if i[2] != p.id_in_group]

                # THEN WE ASSIGN THE HIGHEST PREFERENCE ITEM OF ALL ACCEPTABLE PREFS IN THIS ==== #
                # AND APPEND IT TO THE RESPECTIVE RESOURCE.                                       #
                if len(iterlist) > 0:
                    iteritem = iterlist[0]

                    for n in indices:
                        if iteritem[3] == n:
                            attendants[n - 1].append(iteritem)

                    # FINALLY, THE PREF THAT WAS CONSIDERED IN THIS ROUND IS REMOVED FROM ======= #
                    # ITERLIST AND ALL_PREFS.                                                     #
                    all_prefs.remove(iteritem)
                    iterlist.remove(iteritem)

                else:
                    pass
                pass_i += 1

                for n in indices:
                    attendants[n - 1] = attendants[n - 1][0:Constants.capacities[n - 1]]

        # ASSIGN A RESOURCE TO EACH SUBJECT AND CREATE A DUMMY VARIABLE FOR SUCCESSFUL PREFS IN = #
        # ORDER TO NICELY DISPLAY IT ON RESULTS.HTML.                                             #
        all_attendants_flat = list(chain.from_iterable(attendants))
        for p in players:
            player_resource[p.id_in_group - 1] = [b for b in all_attendants_flat if b[2] == p.id_in_group]
            p.participant.vars['player_resource'] = [i[3] for i in all_attendants_flat if i[2] == p.id_in_group]

    # METHOD: =================================================================================== #
    # SET PAYOFFS =============================================================================== #
    # =========================================================================================== #
    def set_payoffs(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        players = self.get_players()
        indices = [j for j in range(1, Constants.nr_courses + 1)]

        # ADD EVERY VALUE OF A COURSE TO PAYOFF IF IT IS IN THE PLAYERS SCHEDULE ================ #
        for p in players:
            for n in indices:
                if n in p.participant.vars['player_resource']:
                    p.payoff += p.participant.vars['valuations'][n - 1]
                    p.participant.vars['successful'][n - 1] = True


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

    # DYNAMICALLY CREATE N FORM TEMPLATES FOR PREFS ============================================= #
    for j in range(1, Constants.nr_courses + 1):
        locals()['pref_c' + str(j)] = models.IntegerField(label="", min=1)
    del j

    # METHOD: =================================================================================== #
    # PREPARE BIDS IN ORDER TO IMPLEMENT TIE BREAKING =========================================== #
    # =========================================================================================== #
    def prepare_decisions(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        indices = [j for j in range(1, Constants.nr_courses + 1)]

        self.participant.vars['prepared_list'] = []

        for i in Constants.priorities:
            self.participant.vars['prepared_list'].append([(i.index(j) + 1) for j in i if j == self.id_in_group])

        for i in self.participant.vars['prepared_list']:
            i.append(self.id_in_group)

        for i, j in zip(self.participant.vars['prepared_list'], indices):
            i.append(j)

        for i, j in zip(self.participant.vars['prepared_list'], self.participant.vars['player_prefs']):
            i.insert(0, j)
