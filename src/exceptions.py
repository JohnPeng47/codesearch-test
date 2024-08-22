class ClientActionException(Exception):
    """
    Exception type that needs to be displayed and handled in the client
    """
    def __init__(self, *, message, ex: Exception):
        self.message = message
        self.type = ex.__class__.__name__
        
        super().__init__()