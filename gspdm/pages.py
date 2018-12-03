from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
from itertools import chain


# METHOD: =================================================================================== #
# DEFINE VARIABLES USED IN ALL TEMPLATES ==================================================== #
# =========================================================================================== #
def vars_for_all_templates(self):

    return {
        's_len': Constants.s_len,
        'endowment': Constants.endowment,
        'nr_courses': Constants.nr_courses,
        'indices': [j for j in range(1, Constants.nr_courses + 1)],
        'valuations': self.participant.vars['valuations'],
        'valuations_others': zip(self.participant.vars['other_types_names'],
                                 self.participant.vars['valuations_others']),
        'capacities': Constants.capacities,
        'players_per_group': Constants.players_per_group
    }


class Instructions(Page):
    pass


class InstructionsFramed(Page):
    pass


class Decision(Page):

    form_model = 'player'

    # METHOD: =================================================================================== #
    # RETRIEVE FORM FIELDS FROM MODELS.PY ======================================================= #
    # =========================================================================================== #
    def get_form_fields(self):
        form_fields = \
            list(chain.from_iterable([list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1:]))

        return form_fields

    # METHOD: =================================================================================== #
    # CREATE VARIABLES TO DISPLAY ON DECISION.HTML ============================================== #
    # =========================================================================================== #
    def vars_for_template(self):
        indices = [j for j in range(1, Constants.nr_courses + 1)]
        form_fields_prefs = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1]
        form_fields_bids = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][2]
        pref_input = zip(indices, form_fields_prefs)
        bid_input = zip(indices, form_fields_bids)

        return {'indices': indices,
                'pref_input': pref_input,
                'bid_input': bid_input,
                }

    # METHOD: =================================================================================== #
    # BEFORE NEXT PAGE: WRITE BACK PLAYER BIDS AND PREFS TO PARTICIPANT VARS AND PREPARE          #
    # TIE-BREAKER                                                                                 #
    # =========================================================================================== #
    def before_next_page(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        indices = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][0]
        form_fields_prefs = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1]
        form_fields_bids = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][2]

        # DYNAMICALLY WRITE BACK PLAYER BIDS AND PREFS TO LISTS OF BIDS AND PREFS =============== #
        for n, pref in zip(indices, form_fields_prefs):
            choice_i = getattr(self.player, pref)
            self.participant.vars['player_prefs'][n - 1] = int(choice_i)

        for n, bid in zip(indices, form_fields_bids):
            choice_j = getattr(self.player, bid)
            self.participant.vars['player_bids'][n - 1] = int(choice_j)

        # PREPARE BIDS AND PREFS FOR TIE-BREAKING AND FOR THE ALLOCATION ======================== #
        self.player.prepare_decisions()

    # METHOD: =================================================================================== #
    # CONTROL BIDS AND PREFS: SUM OF BIDS MUST NOT EXCEED THE PLAYERS' ENDOWMENT AND PREFS MUST   #
    # BE UNIQUE!                                                                                  #
    # =========================================================================================== #
    def error_message(self, values):
        indices = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][0]
        form_fields_bids = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1]
        form_fields_prefs = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1]
        sum_of_bids = sum([values[i] for i in form_fields_bids])
        sum_of_prefs = sum([values[i] for i in form_fields_prefs])

        if not Constants.enforce_binding:
            if sum_of_bids > Constants.endowment:
                return 'The sum of your bids must not exceed %s!' % Constants.endowment
        else:
            if sum_of_bids != Constants.endowment:
                return 'The sum of your bids must be exactly %s!' % Constants.endowment

        if sum_of_prefs != sum(indices):
            return 'The preferences must be a unique for each item and run from 1 to %s!' % (indices[-1])


class ResultsWaitPage(WaitPage):

    # METHOD: =================================================================================== #
    # AFTER ALL PLAYERS HAVE SUBMITTED BIDS: RUN GSPDM MECHANISM AND SET PLAYERS' PAYOFFS ======= #
    # =========================================================================================== #
    def after_all_players_arrive(self):
        self.group.get_allocation()
        self.group.set_payoffs()

        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        indices = [list(i) for i in zip(*self.session.vars['form_fields_clearing_bids_plus_index'])][0]
        form_fields_clearing_bids = [list(i) for i in zip(*self.session.vars['form_fields_clearing_bids_plus_index'])][1]

        # DYNAMICALLY WRITE BACK CLEARING BIDS TO MODEL FIELDS ================================== #
        for n, bid in zip(indices, form_fields_clearing_bids):
            clearing_bid_i = self.session.vars['clearing_bids'][n - 1]
            setattr(self.group, bid, clearing_bid_i)


class Results(Page):

    # METHOD: =================================================================================== #
    # CREATE VARIABLES TO DISPLAY ON RESULTS.HTML =============================================== #
    # =========================================================================================== #
    def vars_for_template(self):
        player_bids = [i for i in self.participant.vars['player_bids']]
        player_prefs = [i for i in self.participant.vars['player_prefs']]
        successful = [i for i in self.participant.vars['successful']]
        clearing_bids = [i for i in self.session.vars['clearing_bids']]
        payoff = self.player.payoff

        return {
                'player_bids': player_bids,
                'player_prefs': player_prefs,
                'successful': successful,
                'clearing_bids': clearing_bids,
                'payoff': payoff
                }


class Thanks(Page):
    pass


page_sequence = [
    Decision,
    ResultsWaitPage,
    Thanks,
]

if Constants.application_framing:
    if Constants.instructions:
        page_sequence.insert(0, InstructionsFramed)

    if Constants.results:
        page_sequence.insert(-1, Results)

else:
    if Constants.instructions:
        page_sequence.insert(0, Instructions)

    if Constants.results:
        page_sequence.insert(-1, Results)
