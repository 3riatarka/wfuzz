import sqlite3, time, os, re
from itertools import chain

class DatabaseException(Exception):
    pass

def htmlSafe(string):
    return string.replace('&', '&amp;').replace('<', '&lt;').replace(' > ', ' &gt;').replace('"', '&quot;').replace("'", ' &#39;')

class DatabaseHandler(object):
    def __init__(self, dbf, hc, hl, hw, hh):
        self.database_file = dbf
        self.new_database = 0
        self.uri_node = 0
        self.uri = ''
        self.domain_node = 0
        self.domain = ''
        self.wordlists = list()
        self.uri_childs = list()
        self.hc = hc
        self.hl = hl
        self.hw = hw
        self.hh = hh

    def connect(self):
        try:
            # Check if the file already exists:
            if os.path.isfile(self.database_file):
                resp = raw_input("The database file already exists!\nDo you want to add information to %s? [y/N] > " %
                                 self.database_file)
                if resp.lower() != 'y':
                    print("\nSelect another database file then.\nExiting...")
                    exit(0)
                else:
                    print("Appending info to database file...\n")
            else:
                print("Creating database file %s.\n" % self.database_file)
                open(self.database_file, 'a').close()  # Quick way to create empty file
                self.new_database = 1
            self.connection = sqlite3.connect(self.database_file)
        except DatabaseException:
            print("Unable to open database file %s\n" % self.database_file)
            exit(1)

        self.cursor = self.connection.cursor()
        if self.new_database == 1:
            self.createDatabase()

    def checkDatabaseFile(self):
        try:
            tables = ",".join(map(str, chain.from_iterable(self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()))).split(',')
            if "node" not in tables or "children" not in tables: # Tables required for CherryTree
                print("The file %s is not an sqlite3 database with CherryTree format." % (self.database_file))
                exit(1)
        except sqlite3.DatabaseError as ex:
            print("The file %s is not an sqlite3 database with CherryTree format or its database is corrupted: %s" % (self.database_file, ex))
            exit(1)

    def checkIfDBIsEmpty(self):
        nodes = self.cursor.execute("SELECT node_id FROM node;").fetchall()
        if len(nodes) == 0:
            return 1
        else:
            return 0 # Not true

    def checkQuery(self, url, wordlists):
        if self.new_database == 1:
            return 0 # There are no records yet
        queries_text = "".join(map(str, chain.from_iterable(self.cursor.execute("SELECT txt FROM node WHERE name = 'completed_queries';").fetchall()))).split('\n')
        self.wordlists = wordlists
        wordlist = ",".join(wordlists)
        record = ("%s,%s" % (url, wordlist))
        if record in queries_text:
            return 1
        else:
            return 0

    def registerQuery(self, url, wordlists):
        wordlist = ",".join(wordlists)
        record = ("%s,%s\n" % (url,wordlist))
        previous_records = "".join(map(str, chain.from_iterable(self.cursor.execute("SELECT txt FROM node WHERE name = 'completed_queries';").fetchall())))
        if len(previous_records) > 0:
            record += "%s%s" % (previous_records, record)
        record = (record,)
        self.cursor.execute("UPDATE node SET txt = ? WHERE name='completed_queries';", record)
        self.connection.commit()

    def nextNode(self):
        last= "".join(map(str,chain.from_iterable(self.cursor.execute("SELECT node_id FROM node ORDER BY node_id DESC LIMIT 1;").fetchall())))
        return int(last)+1

    def getDomainNode(self):
        self.domain_node = ",".join(map(str, chain.from_iterable(
            self.cursor.execute("SELECT node_id FROM node WHERE name = ?;", (self.domain,)).fetchall())))
        if len(self.domain_node.split(',')) > 1:
            raise DatabaseException("The first level node '%s' is repeated in the database. Exiting..." % self.domain)
        if len(self.domain_node) == 0:  # If it does not exist, create it
            self.domain_node = self.createNode(self.nextNode(), 0, self.domain, '<rich_text></rich_text>')

    def getUriNode(self):
        domain_childs = list("".join(map(str, chain.from_iterable(self.cursor.execute("SELECT name FROM node WHERE node_id = ?;", (id,)).fetchall()))) for id in list(chain.from_iterable(self.cursor.execute("SELECT node_id FROM children WHERE father_id = ?;",(self.domain_node,)).fetchall())))
        if self.uri not in domain_childs:
            self.uri_node = self.createNode(self.nextNode(),self.domain_node,self.uri,'<rich_text></rich_text>')
        else:
            self.uri_node = ",".join(map(str,chain.from_iterable(self.cursor.execute("SELECT node.node_id FROM node, children WHERE node.node_id = children.node_id AND children.father_id = ? AND node.name = ?;", (self.domain_node,self.uri,)).fetchall())))
            if len(self.uri_node.split(",")) > 1:
                raise DatabaseException("The second level node '%s' is repeated in the same domain. Exiting..." % self.uri)

    def write(self, res):
        # Check if the response is filtered
        if res.code in self.hc or res.lines in self.hl or res.words in self.hw or res.chars in self.hh:
            return 0

        # Set domain and URI:
        self.domain = res.history.host
        self.uri = res.url.split(self.domain)[1].rsplit('/',1)[0]+'/'
        # Check if the domain already exists in the database, else create it:
        self.getDomainNode()
        # Check if the URI exists in the domain node, else create it:
        self.getUriNode()

        self.uri_childs = [int(item[0].encode('utf-8')) for item in self.cursor.execute(
            "SELECT node.name FROM node, children WHERE node.node_id = children.node_id AND children.father_id = ?;",
            (self.uri_node,)).fetchall()] # Es mejor este metodo que el de domain_childs?

        create_node = True
        if res.code in self.uri_childs:
            create_node = False

        if str(res.code)[0] == '2': # OK
            text = '<rich_text family="monospace">%06d:\t</rich_text><rich_text family="monospace" link="webs %s">%s\n</rich_text>' % (res.nres, htmlSafe(res.url)[:60], htmlSafe(res.url)[:60])
        elif str(res.code)[0] == '3': # Redirection
            text = '<rich_text family="monospace">%06d:\t%s\t\t->\t\t</rich_text><rich_text family="monospace" link="webs %s">%s\n</rich_text>' % (res.nres, htmlSafe(res.url)[:60], htmlSafe(res.history.headers.response['Location'].encode('utf-8')), htmlSafe(res.history.headers.response['Location'].encode('utf-8')))
        else:
            text = '<rich_text family="monospace">%06d:\t%s\n</rich_text>' % (res.nres, htmlSafe(res.url)[:60])

        if create_node:
            text = "<rich_text family=\"monospace\">%s\n  ID: \t\t\t\t\t\t\t Payload\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t[Redirects to]\n%s\n</rich_text>%s" % ("="*90, "="*90, text)
            code_node = self.createNode(self.nextNode(), self.uri_node, res.code, text)
        else:
            code_node = "".join(map(str, chain.from_iterable(self.cursor.execute("SELECT node.node_id FROM node, children WHERE node.node_id = children.node_id AND children.father_id = ? AND node.name = ?;",(self.uri_node, res.code)).fetchall())))
            code_text = "".join(map(str, chain.from_iterable(self.cursor.execute("SELECT txt FROM node WHERE node_id = ?;", (code_node,)).fetchall())))
            prev_text = re.findall('<node><rich_text.*?>(.*?)</rich_text></node>', code_text, re.S)
            if text in code_text:
                return 0 # Endpoint already registered
            code_text = re.sub('<node><rich_text family="monospace">(.*?)</rich_text></node>', '<node><rich_text family="monospace">%s</rich_text>%s</node>' % (prev_text[0],text), code_text,1,re.DOTALL)

            self.cursor.execute("UPDATE node SET txt = ? WHERE node_id = ?;", (code_text, code_node))
            self.connection.commit()


    def createDatabase(self):
        self.cursor.execute("PRAGMA foreign_keys=OFF;")
        self.cursor.execute("BEGIN TRANSACTION;")

        # Tables needed for CherryTree:
        self.cursor.execute("CREATE TABLE bookmark (node_id INTEGER_UNIQUE, sequence INTEGER);")
        self.cursor.execute("""CREATE TABLE node (
node_id INTEGER UNIQUE,
name TEXT,
txt TEXT,
syntax TEXT,
tags TEXT,
is_ro INTEGER,
is_richtxt INTEGER,
has_codebox INTEGER,
has_table INTEGER,
has_image INTEGER,
level INTEGER,
ts_creation INTEGER,
ts_lastsave INTEGER
);""")
        self.cursor.execute("""CREATE TABLE codebox (
node_id INTEGER,
offset INTEGER,
justification TEXT,
txt TEXT,
syntax TEXT,
width INTEGER,
height INTEGER,
is_width_pix INTEGER,
do_highl_bra INTEGER,
do_show_linenum INTEGER
);""")
        self.cursor.execute("""CREATE TABLE grid (
node_id INTEGER,
offset INTEGER,
justification TEXT,
txt TEXT,
col_min INTEGER,
col_max INTEGER
);""")
        self.cursor.execute("""CREATE TABLE image (
node_id INTEGER,
offset INTEGER,
justification TEXT,
anchor TEXT,
png BLOB,
filename TEXT,
link TEXT,
time INTEGER
);""")
        self.cursor.execute("""CREATE TABLE children (
node_id INTEGER UNIQUE,
father_id INTEGER,
sequence INTEGER
);""")
        self.connection.commit()

    def initializeDatabase(self):
        # Parent node is the domain
        epoc = round(time.time(), 5)
        node_query = (self.domain,epoc,epoc)
        aux_query = (epoc,epoc)
        self.cursor.execute("INSERT INTO node VALUES(1, ?, '<?xml version=\"1.0\" ?><node><rich_text family=\"monospace\"></rich_text></node>','custom-colors','',0,1,0,0,0,0,?,?);",node_query)
        self.cursor.execute("INSERT INTO children VALUES(1,0,1);")
        self.cursor.execute("INSERT INTO node VALUES(2, 'completed_queries', '','custom-colors','',0,1,0,0,0,0,?,?);",aux_query)
        self.cursor.execute("INSERT INTO children VALUES(2,-1,2);") # -1 as parent node to keep this one hidden
        self.connection.commit()

    def createNode(self, id, parent, node_name, node_text):
        if id <= 1:
            raise DatabaseException("Database node creation failed")
        sequence = "".join(map(str, chain.from_iterable(self.cursor.execute("SELECT sequence FROM children WHERE father_id = ? ORDER BY sequence DESC LIMIT 1", (parent,)))))
        if len(sequence) == 0:
            sequence = 0

        try:
            epoc = round(time.time(), 5)
            text = "<?xml version=\"1.0\" ?><node>%s</node>" % node_text
            node_query = (id,node_name,text,epoc,epoc)
            self.cursor.execute("INSERT INTO node VALUES(?,?,?,'custom-colors','',0,1,0,0,0,0,?,?);",node_query)

            child_query = (id, int(parent), int(sequence)+1)
            self.cursor.execute("INSERT INTO children VALUES(?,?,?);", child_query)
            self.connection.commit()
            return id
        except DatabaseException:
            print("Database node creation failed")