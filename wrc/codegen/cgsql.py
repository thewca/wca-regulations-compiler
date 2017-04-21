''' Backend for SQL.  '''
from wrc.sema.ast import WCADocument
from wrc.codegen.cg import CGDocument

CONTINENTS = {
    'AF': '_Africa',
    'AS': '_Asia',
    'EU': '_Europe',
    'NA': '_North America',
    'OC': '_Oceania',
    'SA': '_South America',
}

SEPARATOR = u',\n'
STATE = u"('{name}', '{name}', '{continent}', '{state_id}')"
PREAMBLE = '''# frozen_string_literal: true

sql = "INSERT INTO `Countries` (`id`, `name`, `continentId`, `iso2`) VALUES
'''
POSTAMBLE = u';"\nActiveRecord::Base.connection.execute(sql)\n'


class WCADocumentSQL(CGDocument):
    ''' Implement a simple SQL generator from WCAStates AST. '''

    name = "SQL"
    def __init__(self, versionhash, language, pdf):
        # We don't need them
        del versionhash, language, pdf
        super(WCADocumentSQL, self).__init__(str)
        self.first = True

    def emit(self, states, _):
        self.codegen += PREAMBLE
        self.visit(states)
        self.codegen += POSTAMBLE
        return [self.codegen]


    def visitState(self, state):
        if self.first:
            self.first = False
        else:
            self.codegen += SEPARATOR
        self.codegen += STATE.format(name=state.name,
                                     continent=CONTINENTS[state.continent_id],
                                     state_id=state.state_id)
        retval = super(WCADocumentSQL, self).visitState(state)
        return retval

