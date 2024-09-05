from watchdog.observers import Observer
from watchdog.events import FileModifiedEvent, PatternMatchingEventHandler
from threading import Timer
from subprocess import Popen
from sys import argv

# Grab the script name from a command line arg.
SCRIPT_FILENAME = argv[1]


class Runner:
    __proc = None
    __handler_func = None

    # Command to run the passed in script.
    @staticmethod
    def run():
        # Run the python script and keep track of the process.
        Runner.__proc = Popen(["python", SCRIPT_FILENAME])

    # Fires when watched files change.
    @staticmethod
    def handle_file_modified(event):

        # If there is previously running process
        # from a previous reload then kill it.
        if Runner.__proc != None:
            Runner.__proc.kill()

        # Debouncing:

        # If there is a script reload scheduled
        # to occur in the future, cancel it.
        if Runner.__handler_func != None:
            Runner.__handler_func.cancel()

        # Schedule the reload to happen in .5 secs.
        Runner.__handler_func = Timer(1, Runner.run)
        Runner.__handler_func.start()


# Run our passed in script.
Runner.run()

# Initialize file watching object.
file_watcher = Observer()

# Designate our event handler as one that
# activates when any .py files indirectory are changed,
# exluding this one.
file_modified_event_handler = PatternMatchingEventHandler(patterns=["./*.py"], ignore_patterns=["./reloadable.py"])

# Set the action to be taken when the "on_modified" action
# is detected (our debouncing method is called).
file_modified_event_handler.on_modified = Runner.handle_file_modified

# Initialize the file watching.
file_watcher.schedule(file_modified_event_handler, ".", recursive=True)
file_watcher.start()


try:
    while file_watcher.is_alive():
        file_watcher.join(1)
except KeyboardInterrupt:
    file_watcher.stop()

file_watcher.join()