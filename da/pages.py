from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
from itertools import chain


# METHOD: =================================================================================== #
# DEFINE VARIABLES USED IN ALL TEMPLATES ==================================================== #
# =========================================================================================== #
def vars_for_all_templates(self):
    return {
        'nr_courses': Constants.nr_courses,
        'players_per_group': Constants.players_per_group,
        'indices': [j for j in range(1, Constants.nr_courses + 1)],
        'valuations': self.participant.vars['valuations'],
        'valuations_others': zip(self.participant.vars['other_types_names'],
                                 self.participant.vars['valuations_others']),
        'priorities': self.participant.vars['priorities'],
        'capacities': Constants.capacities
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
        form_fields = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1]

        return {
                'form_fields': form_fields
                }

    # METHOD: =================================================================================== #
    # BEFORE NEXT PAGE: WRITE BACK PLAYER PREFS TO PARTICIPANT VARS ============================= #
    # =========================================================================================== #
    def before_next_page(self):
        # CREATE INDICES FOR MOST IMPORTANT VARS ================================================ #
        indices = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][0]
        form_fields = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1]

        # DYNAMICALLY WRITE BACK PLAYER PREFS TO A LIST OF PREFS ================================ #
        for n, pref in zip(indices, form_fields):
            choice_i = getattr(self.player, pref)
            self.participant.vars['player_prefs'][n - 1] = int(choice_i)

        # PREPARE PREFS FOR THE ALLOCATION ====================================================== #
        self.player.prepare_decisions()

    # METHOD: =================================================================================== #
    # CONTROL PREFS: PREFERENCES MUST BE UNIQUE ================================================= #
    # =========================================================================================== #
    def error_message(self, values):
        indices = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][0]
        form_fields = [list(i) for i in zip(*self.participant.vars['form_fields_plus_index'])][1]
        sum_of_prefs = sum([values[i] for i in form_fields])

        if sum_of_prefs != sum(indices):
            return 'The preferences must be a unique for each item and run from 1 to %s!' % (indices[-1])


class ResultsWaitPage(WaitPage):

    # METHOD: =================================================================================== #
    # AFTER ALL PLAYERS HAVE SUBMITTED PREFS: RUN DA MECHANISM AND SET PLAYERS' PAYOFFS ========= #
    # =========================================================================================== #
    def after_all_players_arrive(self):
        self.group.get_allocation()
        self.group.set_payoffs()


class Results(Page):

    # METHOD: =================================================================================== #
    # CREATE VARIABLES TO DISPLAY ON RESULTS.HTML =============================================== #
    # =========================================================================================== #
    def vars_for_template(self):
        player_prefs = [i for i in self.participant.vars['player_prefs']]
        successful = [i for i in self.participant.vars['successful']]

        return {
                'player_prefs': player_prefs,
                'successful': successful
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
