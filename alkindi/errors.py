
class ApplicationError(RuntimeError):

    def __str__(self):
        if type(self.args) == tuple:
            return str(self.args[0])
        return str(self.args)


class ModelError(ApplicationError):
    pass


class ApiError(ApplicationError):
    pass
