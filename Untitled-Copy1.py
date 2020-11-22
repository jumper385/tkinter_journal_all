#%%
import sqlite3
import datetime as dt
from uuid import uuid4

def init_db_cursor(dbname):
    conn = sqlite3.connect(dbname)
    cursor = conn.cursor()
    return conn, cursor

db, c = init_db_cursor('journal.db')

def make_tag(db, cursor, tag):
    _id = uuid4()
    
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS tag (
            tagid text PRIMARY KEY,
            name text
        )
    """)
    
    if tag:
        cursor.execute(f"""
            INSERT INTO tag (tagid, name)
            VALUES ('{_id}', '{tag}')
        """)
    
        db.commit()
    
    return _id

def edit_tag(db, cursor, tagid, name):
    cursor.execute(f"""
        UPDATE tag
        SET name='{name}'
        WHERE tagid='{tagid}'
    """)
    db.commit()

def get_tag(db, cursor, query=None):
    if query:
        cursor.execute(f"""
            SELECT * FROM tag
            WHERE {', '.join(f"{key}='{value}'" for key, value in query.items())}
        """)
    else:
        cursor.execute(f"""
            SELECT * FROM tag
        """)
    return c.fetchone()

def delete_tag(db, cursor, tagid):
    cursor.execute(f"""
        DELETE FROM tag
        WHERE tagid='{tagid}'
    """)
    db.commit()

def make_entry_tag(db, cursor, entryid, tagid):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entry_tag (
            entryid text,
            tagid text, 
            FOREIGN KEY (entryid)
                REFERENCES entry (id)
            FOREIGN KEY (tagid)
                REFERENCES tag (id)
        )
    """)
    cursor.execute(f"""
        INSERT INTO entry_tag (entryid, tagid)
        VALUES ('{entryid}', '{tagid}')
    """)
    
    db.commit()

def delete_entry_tag(db, cursor, entryid, tagid):
    cursor.execute(f"""
        DELETE FROM entry_tag
        WHERE entryid='{entryid}' {f"AND tagid='{tagid}'" if tagid else ''}
    """)
    db.commit()

def make_entry_collection(db, cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entry (
            id text PRIMARY KEY, 
            title text,
            entry text,
            is_action boolean, 
            timestamp date,
            tags text,
            completed boolean
        )
    """)
    db.commit()
    
make_entry_collection(db, c)

def make_entry(db, cursor, entries):
    _id = uuid4()
    
    defaults = {
        'id':_id,
        'is_action':False,
        'timestamp':dt.datetime.now()
    }
    
    entry = {**defaults, **entries}
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entry (
            id text PRIMARY KEY, 
            title text,
            entry text,
            is_action boolean, 
            timestamp date
        )
    """)
    
    cursor.execute(f"""
        INSERT INTO entry ({', '.join([x for x in entry.keys()])})
        VALUES ({', '.join([f"'{x}'" for x in entry.values()])})
    """)
    
    db.commit()
    return _id

def delete_entry(db, cursor, _id):
    cursor.execute(f"""
        DELETE FROM entry
        WHERE id='{_id}'
    """)
    db.commit()

def edit_entry(db, cursor, _id, delta):
    print(delta)
    delta_string = ", ".join([f"""{field} = '{data}'""" for field, data in delta.items()])
    cursor.execute(f"""
        UPDATE entry
        SET {delta_string}
        WHERE id='{_id}'
    """)
    db.commit()

def get_entry(db, cursor, fields=None, query=None):
    if query:
        query_string = ", ".join([f"{key}='{value}'" for key,value in query.items()])
        cursor.execute(f"""
            SELECT {', '.join(fields)} FROM entry
            WHERE {query_string}
        """)
    else: 
        cursor.execute(f"""
            SELECT {', '.join(fields)} FROM entry
        """)
    formatted = [dict(zip(fields, values)) for values in c.fetchall()]
    return formatted

def make_note(db, cursor, entry):
    tags = entry['tags']
    note = {key:value for key,value in entry.items() if key != 'tags'}
    _id = make_entry(db, cursor, note)
    make_tag(db,cursor,None)
    
    for tag in tags:
        tag_query = get_tag(db, c, {'name':tag})

        if tag_query:
            tagid, name = tag_query
        else: 
            tagid = make_tag(db,c,tag)
        
        make_entry_tag(db, c, _id, tagid)
    
    return _id

def delete_note(db, cursor, entryid):
    delete_entry(db, cursor, entryid)
    delete_entry_tag(db, cursor, entryid, None)

def get_string_note(db, cursor, string_query):
    cursor.execute(f"""
        SELECT * FROM entry
        WHERE entry LIKE '%{string_query}%' OR title LIKE '%{string_query}%'
    """)
    return cursor.fetchall()
#%%
import tkinter as tk
from tkinter import *
#%%
root = Tk()

entries = []
actions = []
entry_listings = []
action_listings = []

# ENTRY CREATION
entry_create_frame = LabelFrame(text="(1) Create New Entry")
entry_create_frame.grid(column=0, row=0)

Label(entry_create_frame, text="Entry Title").grid(column=0, row=0)
entry_title = Entry(entry_create_frame)
entry_title.grid(column=1, row=0)

Label(entry_create_frame, text="Entry Contents").grid(column=0, row=1)
entry_content = Entry(entry_create_frame)
entry_content.grid(column=1, row=1)

Label(entry_create_frame, text="Entry Date").grid(column=0, row=2)
entry_date = Entry(entry_create_frame)
entry_date.grid(column=1, row=2)

Label(entry_create_frame, text="Entry Tags").grid(column=0, row=3)
entry_tags = Entry(entry_create_frame)
entry_tags.grid(column=1, row=3)

entry_actionable = BooleanVar(False)
Label(entry_create_frame, text="Is Actionable").grid(column=0, row=4)
Checkbutton(entry_create_frame, variable = entry_actionable, onvalue=True).grid(column=1, row=4)

# id text PRIMARY KEY, 
# title text,
# entry text,
# is_action boolean, 
# timestamp date,

def refresh_content():
    entry_title.delete(0, 'end')
    entry_content.delete(0, 'end')
    entry_date.delete(0,'end')
    entry_actionable.set(False)
    entry_tags.delete(0,'end')
    
    entry_date.insert(0, dt.datetime.strftime(dt.datetime.now(), "%d/%m/%Y %H:%M"))
    
    entry_list.delete(0, END)
    entries = get_entry(db, c, ['id','timestamp','title', 'is_action'], {'is_action':'False'})
    
    action_list.delete(0, END)
    actions = get_entry(db, c, ['id','timestamp','title', 'is_action'], {'is_action':'True'})
    
    entry_listings = map(lambda x: x['id'], entries)
    [entry_list.insert(index, entry['id'] or "*UNTITLED*") for index, entry in enumerate(entries)]
    
    action_listings = map(lambda x: x['id'], actions)
    [action_list.insert(index, entry['id'] or '*UNTITLED*') for index, entry in enumerate(actions)]

def create_entry():
    print(entry_title.get())
    print(entry_content.get())
    print(entry_date.get())
    print(entry_actionable.get())
    
    make_note(db, c, {
        "id":uuid4(),
        "title":entry_title.get(),
        "entry":entry_content.get(),
        "is_action":entry_actionable.get(),
        "tags":entry_tags.get(),
        "timestamp":dt.datetime.strptime(entry_date.get(), "%d/%m/%Y %H:%M") if entry_date.get() != "" else dt.datetime.now()
    })
    
    refresh_content()
    
Button(entry_create_frame, text="Submit", command=create_entry).grid(column=0, row=5, columnspan=2)

# ENTRY LIST
entry_list_frame = LabelFrame(text="(2a) View Recent Entries")
entry_list_frame.grid(column=1, row=0)
entry_list = Listbox(entry_list_frame)
entry_list.grid(column=0, row=0)

def print_entry_listings():
    array_index, = entry_list.curselection()
    print(array_index)
    new_selection = get_entry(db, c, ['id','timestamp','title','entry'], {"id":entry_listings[array_index]})
    entry_selection = new_selection[0]
    ev_title['text'] = entry_selection['title'] or "*UNTITLED*"
    ev_entry['text'] = entry_selection['entry'] or "*NO ENTRY*"
    ev_timestamp['text'] = entry_selection['timestamp']

Button(entry_list_frame, text='View Selected', command=print_entry_listings).grid(column=0, row=1)

# ACTION LIST
action_list_frame = LabelFrame(text="(2b) Actions List")
action_list_frame.grid(column=2, row=0)
action_list = Listbox(action_list_frame)
action_list.grid(column=0, row=0)
    
def print_action_listings():
    array_index, = action_list.curselection()
    entry_selection = get_entry(db, c, ['id','timestamp','title','entry'], {"id":action_listings[array_index]})[0]
    ev_title['text'] = entry_selection['title'] or "*UNTITLED*"
    ev_entry['text'] = entry_selection['entry'] or "*NO ENTRY*"
    ev_timestamp['text'] = entry_selection['timestamp']

Button(action_list_frame, text='View Selected', command=print_action_listings).grid(column=0, row=1)

refresh_content()

# ENTRY VIEW
entry_view_frame = LabelFrame(text="(3) View Selected Entry")
entry_view_frame.grid(column=3, row=0)

Label(entry_view_frame, text="Title").grid(column=0, row=0)
ev_title = Label(entry_view_frame, text="Select an Entry")
ev_title.grid(column=1, row=0)

Label(entry_view_frame, text="Timestamp").grid(column=0, row=1)
ev_timestamp = Label(entry_view_frame, text="No timestamp available")
ev_timestamp.grid(column=1, row=1)

Label(entry_view_frame, text="Entry").grid(column=0, row=2)
ev_entry = Label(entry_view_frame, text="No entry selected")
ev_entry.grid(column=1, row=2)

root.mainloop()


# In[ ]:




