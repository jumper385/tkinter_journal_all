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

entry_listings = []
action_listings = []

root = Tk()

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

def refresh_entries():

    actions = get_entry(db, c, ['id', 'title'], {'is_action':'True'})
    action_ids = set(map(lambda x: x['id'], actions))
    diff = [*action_ids - set(action_listings)]
    [action_listings.append(x) for x in diff]
    action_titles = [get_entry(db, c, ['title'], {'id':x})[0]['title'] or "UNTITLED" for x in action_listings[::-1]]
    action_list.delete(0,END)
    [action_list.insert(index, entry) for index, entry in enumerate(action_titles)]

    entries = get_entry(db, c, ['id', 'title'], {'is_action':'False'})
    entry_ids = set(map(lambda x: x['id'], entries))
    diff = [*entry_ids - set(entry_listings)]
    [entry_listings.append(x) for x in diff]
    entry_titles = [get_entry(db, c, ['title'], {'id':x})[0]['title'] or "UNTITLED" for x in entry_listings[::-1]]
    entry_list.delete(0,END)
    [entry_list.insert(index, entry) for index, entry in enumerate(entry_titles)]
        
def create_entry():    
    
    new_entry = {
        'id': uuid4(),
        'title':entry_title.get(),
        'entry':entry_content.get(),
        'is_action':entry_actionable.get(),
        'tags':entry_tags.get().strip().split(';'),
        'timestamp':dt.datetime.strptime(entry_date.get(), "%d/%m/%Y %H:%M") if entry_date.get() != "" else dt.datetime.now()
    }
    
    entry_title.delete(0,END)
    entry_content.delete(0,END)
    entry_content.delete(0,END)
    entry_actionable.set(False)
    entry_tags.delete(0,END)
    entry_date.delete(0,END)
    
    new_id = make_note(db, c, new_entry)
    print(new_id)
    refresh_entries()

Button(entry_create_frame, text="Submit", command=create_entry).grid(column=0, row=5, columnspan=2)

# ENTRY LIST
entry_list_frame = LabelFrame(text="(2a) View Recent Entries")
entry_list_frame.grid(column=1, row=0)
entry_list = Listbox(entry_list_frame)
entry_list.grid(column=0, row=0)

def view_entry():
    index, = entry_list.curselection()
    entry_result = get_entry(db, c, ['title','timestamp','id','is_action','entry'], {'id':entry_listings[::-1][index]})[0]
    
    ev_title.delete(0,END)
    ev_timestamp.delete(0,END)
    ev_entry.delete(0,END)
    
    ev_title.insert(0, entry_result['title'])
    ev_timestamp.insert(0, entry_result['timestamp'])
    ev_entry.insert(0, entry_result['entry'])
    ev_is_action.set(entry_result['is_action'] == 'True')
    selected_id.set(entry_listings[::-1][index])

Button(entry_list_frame, text='View Selected', command=view_entry).grid(column=0, row=1)

# ACTION LIST
action_list_frame = LabelFrame(text="(2b) Actions List")
action_list_frame.grid(column=2, row=0)
action_list = Listbox(action_list_frame)
action_list.grid(column=0, row=0)

def view_action():
    index, = action_list.curselection()
    entry_result = get_entry(db, c, ['title','timestamp','id','is_action','entry'], {'id':action_listings[::-1][index]})[0]
    
    ev_title.delete(0,END)
    ev_timestamp.delete(0,END)
    ev_entry.delete(0,END)
        
    ev_title.insert(0,entry_result['title'])
    ev_timestamp.insert(0,entry_result['timestamp'])
    ev_entry.insert(0,entry_result['entry'])
    ev_is_action.set(entry_result['is_action'] == 'True')
    selected_id.set(action_listings[::-1][index])
    
    
Button(action_list_frame, text='View Selected', command=view_action).grid(column=0, row=1)

# ENTRY VIEW
selected_id = StringVar()

entry_view_frame = LabelFrame(text="(3) View Selected Entry")
entry_view_frame.grid(column=3, row=0)

Label(entry_view_frame, text="Title").grid(column=0, row=0)
ev_title = Entry(entry_view_frame, text="Select an Entry")
ev_title.insert(0,'Select an Entry')
ev_title.grid(column=1, row=0)
    
Label(entry_view_frame, text="Timestamp").grid(column=0, row=1)
ev_timestamp = Entry(entry_view_frame)
ev_timestamp.insert(0,'No timestamp available')
ev_timestamp.grid(column=1, row=1)

Label(entry_view_frame, text="Entry").grid(column=0, row=2)
ev_entry = Entry(entry_view_frame)
ev_entry.insert(0,'No entry selected')
ev_entry.grid(column=1, row=2)

ev_is_action = BooleanVar(False)
Label(entry_view_frame, text="Is Actionable").grid(column=0, row=3)
ev_actionable = Checkbutton(entry_view_frame, variable=ev_is_action)
ev_actionable.grid(column=1, row=3)

ev_is_completed = BooleanVar(False)
Label(entry_view_frame, text="Completed").grid(column=0, row=4)
ev_actionable = Checkbutton(entry_view_frame, variable=ev_is_completed)
ev_actionable.grid(column=1, row=4)

def update_entry():
    
    delta = {
        'title':ev_title.get(),
        'entry':ev_entry.get(),
        'timestamp': ev_timestamp.get(),
        'is_action':ev_is_action.get(),
        'completed':ev_is_completed.get()
    }
    
    entry_id = selected_id.get()
    print(delta)
    edit_entry(db, c, entry_id, delta)
    refresh_entries()
    
Button(entry_view_frame, text='Update', command=update_entry).grid(column=0,row=5, columnspan=2)

refresh_entries()

root.mainloop()
# %%
