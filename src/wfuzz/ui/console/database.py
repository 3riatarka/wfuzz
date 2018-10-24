import sqlite3

class DatabaseException(Exception):
    pass

class DatabaseHandler(object):
    def __init__(self, dbf):
        self.database_file = dbf

    def connect(self):
        try:
            self.connection = sqlite3.connect(self.database_file)
        except DatabaseException:
            print("Unable to connect to database file %s\n" % self.database_file)
        self.cursor = self.connection.cursor()

    def createDatabase(self, domain):
        self.cursor.execute("""PRAGMA foreign_keys=OFF;BEGIN TRANSACTION;""")

        # Tables needed for CherryTree:
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
level INTEGER
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
        node_query = (domain,)
        self.cursor.execute("INSERT INTO node VALUES(1, ?, '<?xml version=\"1.0\" ?><node><rich_text></rich_text></node>','custom-colors','',0,1,0,0,0,0);",node_query)
        self.cursor.execute("INSERT INTO children VALUES(1,0,1);")

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