import sqlite3, time

class DatabaseException(Exception):
    pass

class DatabaseHandler(object):
    def __init__(self, dbf):
        self.database_file = dbf
        self.new_database = 0

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.database_file)
        except DatabaseException:
            print("Unable to open database file %s\n" % self.database_file)

        self.cursor = self.connection.cursor()

        # Test if it is a sqlite3 database
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        except sqlite3.DatabaseError as ex:
            print("The file %s is not an sqlite3 database: %s" % (self.database_file, ex))
            exit(0)

    def checkIfDBIsEmpty(self):
        nodes = self.cursor.execute("SELECT node_id FROM node;").fetchall()
        if len(nodes) == 0:
            return 1
        else:
            return 0 # Not true

    def checkRecord(self, domain, uri, query, wordlists):

        # Check if the domain is a node in the database
        domain_query = (domain, )
        domain_node = self.cursor.execute("SELECT node_id FROM node WHERE name = ?;", domain_query).fetchall() # Devuelve una lista con tuplas!
        if not domain_node:
            return 0
        elif len(domain_node) != 1:
            raise DatabaseException("The domain %s is repeated in the database. Exiting..." % domain)
        domain_node = domain_node[0][0]

        # Check if the URI is a node as a domain child
        uri_query = (uri,)
        uri_node = self.cursor.execute("SELECT node_id FROM node WHERE name = ?;", uri_query).fetchall()[0][0]
        domain_childs = self.cursor.execute("SELECT node_id FROM children WHERE father_id = %d" % domain_node).fetchall()

        uri_found = 0
        for child in domain_childs:
            if uri_node == child[0]:
                uri_found = 1
                break

        if uri_found == 0:
            return 0

        # Fix to set a FUZZ node below the URI
        fuzz_query = ('FUZZ',)
        fuzz_node = self.cursor.execute("SELECT node_id FROM children WHERE father_id = %d" % uri_node).fetchall()[0][0]

        # Check if the query is already registered in the tuple domain+uri, worldlists
        fuzz_child_nodes = self.cursor.execute("SELECT node_id FROM children WHERE father_id = %d" % fuzz_node).fetchall()
            # Convert to list:
        child_list = list()
        for node in fuzz_child_nodes:
            child_list.append(node[0])
        fuzz_child_nodes = child_list

        query_query = ('query',)
        query_node_list = self.cursor.execute("SELECT node_id FROM node WHERE name = ?;", query_query).fetchall()
        query_node = ''
        for node in query_node_list:
            if node[0] in fuzz_child_nodes:
                query_node = node[0]
        if query_node == '':
            return 2 # No existe el nodo "query" dentro del FUZZ del dominio? > Error

        query_text = self.cursor.execute("SELECT txt FROM node WHERE node_id = %d;", query_node).fetchall() # Por que falla?
        print(query_text)

        # Queda buscar en query_text si esta la query hecha.

    def createDatabase(self, domain):
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

        # Parent node is the domain - USAR FUZZREQUESTPARSE
        epoc = round(time.time(), 5)
        node_query = (domain,epoc,epoc)
        self.cursor.execute("INSERT INTO node VALUES(1, ?, '<?xml version=\"1.0\" ?><node><rich_text></rich_text></node>','custom-colors','',0,1,0,0,0,0,?,?);",node_query)
        self.cursor.execute("INSERT INTO children VALUES(1,0,1);")
        self.connection.commit()

    def createNode(self, id, parent, node_name, node_text):
        # parent es un ID, o el nombre?
        if id <= 1:
            raise DatabaseException("Database node creation failed")
        father = (parent,)
        sequence_query = ("SELECT sequence FROM children WHERE father_id == ? ORDER BY sequence DESC LIMIT 1;")
        sequence = self.cursor.execute(sequence_query, father).fetchone()

        try:
            node_query = (id,node_name,node_text)
            self.cursor.execute("INSERT INTO node VALUES(?,?,'<?xml version=\"1.0\" ?><node><rich_text>?</rich_text></node>','custom-colors','',0,1,0,0,0,0);",node_query)

            child_query = (id, parent, sequence)
            self.cursor.execute("INSERT INTO children VALUES(?,?,?);", child_query)
        except DatabaseException:
            print("Database node creation failed")