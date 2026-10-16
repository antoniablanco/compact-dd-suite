import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
sys.path.append(parent_dir)

from SourceCode.DDSemiBuilder.AbstractSemiDDBuilder import AbstractSemiDDBuilder

class ExactSemiDDBuilder(AbstractSemiDDBuilder):
    '''
    Concrete class that inherits from AbstractSemiDDBuilder, generating the exact construction of a semi decision diagram.
    '''

    def _specific_end_of_layer_function(self, graph: 'Graph') -> None:
        '''
        Specific end of layer function for the construction of semi decision diagrams.
        Not implemented
        '''
        pass

    def _specific_end_of_construction_function(self) -> None:
        '''
        Specific end of construction function for the construction of semi decision diagrams.
        Removes the nodes left without a root-terminal path after the connection.
        '''
        self._prune_graph()
