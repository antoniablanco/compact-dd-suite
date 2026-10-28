class MaxFlowNotExecuted(Exception):
    def __init__(self, message="MaxFlow has not been executed"):
        self.message = message
        super().__init__(self.message)

class ObjectiveFunctionNotExecuted(Exception):
    """
    Exception raised when the objective function has not been executed.
    """
    def __init__(self, message="The Objective Function has not been executed yet"):
        self.message = message
        super().__init__(self.message)
class NotImplementedError(Exception):
    """
    Exception raised when attempting to call a method that is not implemented.
    """
    def __init__(self, method_name):
        self.message = f"The method '{method_name}' is not implemented"
        super().__init__(self.message)
class ParametersNotSetException(Exception):
    """
    Exception raised when the algorithm parameters have not been set.
    """
    def __init__(self, message="Objective has not been set, please use solve_path()"):
        self.message = message
        super().__init__(self.message)

class NoCutsFound(Exception):
    """
    Exception raised when no cuts were found.
    """
    def __init__(self, message="No cuts were found"):
        self.message = message
        super().__init__(self.message)

class NoCutStrengthening(Exception):
    """
    Exception raised when no strengthened cut was found.
    """
    def __init__(self, message="No strengthened cut was found"):
        self.message = message
        super().__init__(self.message)
class NoGraphFound(Exception):
    """
    Exception raised when no graph is found.
    """
    def __init__(self, message="No graph was found, please create a graph first"):
        self.message = message
        super().__init__(self.message)

class GraphAlreadyExists(Exception):
    """
    Exception raised when a graph already exists and another one cannot be created.
    """
    def __init__(self, message="A graph already exists, you can't create another one"):
        self.message = message
        super().__init__(self.message)

class GurobiModelNotInitialized(Exception):
    """
    Exception raised when the Gurobi model could not be initialized.
    Typical causes include a missing or invalid Gurobi license, a failed
    installation, or an internal Gurobi error during model creation.
    """
    def __init__(self, message="Gurobi model not initialized (possible license issue)"):
        self.message = message
        super().__init__(self.message)

class SemiDDNotSupported(Exception):
    """
    Exception raised when a semi decision diagram is requested for a problem that does not
    implement the methods it requires (e.g. the connection function).
    """
    def __init__(self, problem_name, missing_methods):
        self.message = (f"The problem '{problem_name}' does not support semi decision diagrams, "
                        f"missing: {', '.join(missing_methods)}")
        super().__init__(self.message)

class InfeasibleInstance(Exception):
    """
    Exception raised when the instance is known to have no feasible solution before building
    any decision diagram (e.g. a set cover restriction that no variable covers).
    """
    def __init__(self, message="The instance has no feasible solution"):
        self.message = message
        super().__init__(self.message)
