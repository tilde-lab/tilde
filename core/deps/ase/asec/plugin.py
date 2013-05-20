from ase.asec.run import RunCommand

class PluginCommand(RunCommand):
    def __init__(self, logfile, args, calculate_function):
        RunCommand.__init__(self, logfile, args)
        self.calculate_function = calculate_function

    def calculate(self, atoms, name):
        data = self.calculate_function(atoms, name)
        if data is None:
            data = {}
        return data
