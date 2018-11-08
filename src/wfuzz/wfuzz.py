#!/usr/bin/env python
import sys

from .core import Fuzzer
from .facade import Facade
from .exception import FuzzException, FuzzExceptBadInstall

from .ui.console.mvc import Controller, KeyPress, View
from .ui.console.common import help_banner2
from .ui.console.clparser import CLParser
from .ui.console.database import DatabaseHandler


def main():
    kb = None
    fz = None
    printer = None
    session_options = None
    db = None

    try:
        # parse command line
        session_options = CLParser(sys.argv).parse_cl().compile()
        session_options["send_discarded"] = True

        # Check database file, if enabled, before sending any request
        if session_options["database"]:
            hc = session_options['hc']
            db = DatabaseHandler(session_options['database'], session_options['hc'],session_options['hl'],session_options['hw'],session_options['hh']) # Create database handler
            db.connect() # connect to the database file (checking if the file exists)
            db.checkDatabaseFile() # Check if it is a valid database
            url = session_options.data["url"]
            wordlists = [dic[1]['fn'] for dic in session_options.data['payloads']]
            if db.checkQuery(url, wordlists):
                print("This endpoint is already fuzzed with that wordlist(s)")
                exit(0)

        # Create fuzzer's engine
        fz = Fuzzer(session_options)

        if session_options["interactive"]:
            # initialise controller
            try:
                kb = KeyPress()
            except ImportError as e:
                raise FuzzExceptBadInstall("Error importing necessary modules for interactive mode: %s" % str(e))
            else:
                Controller(fz, kb)
                kb.start()

        printer = View(session_options)
        if session_options["console_printer"]:
            printer = Facade().printers.get_plugin(session_options["console_printer"])(None)
        printer.header(fz.genReq.stats)

        # Initialise database handler:
        if session_options["database"]:
            # Get domain, URI, and wordlists:
            db.domain = fz.genReq.seed.history.host
            db.uri = fz.genReq.seed.history.path.split('FUZZ')[0]

            # Initialize database if needed:
            if db.checkIfDBIsEmpty():
                db.initializeDatabase()

        for res in fz:
            printer.result(res)
            if session_options["database"]:
                db.write(res)

        # If the fuzzing is complete, save it in the database as completed
        if session_options["database"]:
            db.registerQuery(url, wordlists)



        printer.footer(fz.genReq.stats)
    except FuzzException as e:
        print("\nFatal exception: {}".format(str(e)))
    except KeyboardInterrupt:
        print("\nFinishing pending requests...")
        if fz:
            fz.cancel_job()
    except NotImplementedError as e:
        print("\nFatal exception: Error importing wfuzz extensions")
    except Exception as e:
        print("\nUnhandled exception: {}".format(str(e)))
    finally:
        if session_options:
            session_options.close()
        if kb:
            kb.cancel_job()
        Facade().sett.save()


def main_filter():
    def usage():
        print(help_banner2)
        print("""Usage:
\n\twfpayload [Options]\n\n
\nOptions:\n
\t--help              : This help
\t--slice <filter>    : Filter payload\'s elements using the specified expression.
\t-z payload          : Specify a payload for each FUZZ keyword used in the form of type,parameters,encoder.
\t		      A list of encoders can be used, ie. md5-sha1. Encoders can be chained, ie. md5@sha1.
\t		      Encoders category can be used. ie. url
\t--zP <params>	    : Arguments for the specified payload (it must be preceded by -z or -w).
\t-w wordlist         : Specify a wordlist file (alias for -z file,wordlist).
\t-m iterator         : Specify an iterator for combining payloads (product by default)
""")

    from .api import payload
    from .exception import FuzzExceptBadOptions
    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hz:m:w:", ["help", "slice=", "zP="])
    except getopt.GetoptError as err:
        print((str(err)))
        usage()
        sys.exit(2)

    if len(opts) == 0 or len(args) > 0:
        usage()
        sys.exit()

    for o, value in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()

    try:
        for res in payload(**CLParser(sys.argv).parse_cl()):
            if len(res) > 1:
                raise FuzzExceptBadOptions("wfpayload can only be used to generate one word dictionaries")
            else:
                r = res[0]

            if "FuzzResult" in str(r.__class__):
                r._description = r.url

            print(r)

    except KeyboardInterrupt:
        pass
    except FuzzException as e:
        print(("\nFatal exception: %s" % str(e)))
    except Exception as e:
        print(("\nUnhandled exception: %s" % str(e)))


def main_encoder():
    def usage():
        print(help_banner2)
        print("Usage:")
        print("\n\twfencode --help This help")
        print("\twfencode -d decoder_name string_to_decode")
        print("\twfencode -e encoder_name string_to_encode")
        print()

    from .api import encode, decode
    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "he:d:", ["help"])
    except getopt.GetoptError as err:
        print((str(err)))
        usage()
        sys.exit(2)

    if len(args) == 0:
        usage()
        sys.exit()

    try:
        for o, value in opts:
            if o == "-e":
                print((encode(value, args[0])))
            elif o == "-d":
                print((decode(value, args[0])))
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
    except IndexError as e:
        usage()
        print("\nFatal exception: Specify a string to encode or decode.\n")
        sys.exit()
    except AttributeError as e:
        print("\nEncoder plugin missing encode or decode functionality.")
    except FuzzException as e:
        print(("\nFatal exception: %s" % str(e)))


def main_gui():
    import wx
    from .ui.gui.guicontrols import WfuzzFrame
    from .ui.gui.controller import GUIController

    app = wx.App(False)

    frame = WfuzzFrame(None, wx.ID_ANY, "WFuzz wxPython Console", size=(750, 590))
    GUIController(frame)

    frame.Show()
    app.MainLoop()
