from re import RegexFlag
import sqlite3
from sqlite3 import Error
import string
from flask import Flask, request, render_template, session, redirect, url_for, current_app, g
import pandas as pd
import pickle
from wtforms import RadioField
from wtforms.validators import InputRequired
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
import os

#first declare a flask app
app = Flask(__name__)
app.secret_key = "12345"
db_conn = None
ml_model = pickle.load((open("personality.pkl", 'rb')))
total_question = 4
# To create connection with the database file.
def create_connection():
    """ create a database connection to the SQLite database in memory
    :return: Connection object or None
    """
    conn = None
    try:
        if db_conn == None:
            conn = sqlite3.connect("database.db", check_same_thread=False)
            return conn
        else:
            return db_conn
    except Error as e:
        print(e)

    return conn

## To execute update, delete and create queries. We can have seprate funtion as well for a short implementtion I am using just one function.
def execute_db(db_conn, *args):
    data = True
    try:
        with db_conn:
            cur = db_conn.cursor()
            args = list(args)
            args = tuple(args)
            cur.execute(*args)
            arg = args[0].split()[0].lower()
            if arg == 'select':
                data = cur.fetchall()
    except Exception as why:
        data = False
    return data

create_question_table = """ CREATE TABLE IF NOT EXISTS questions (
                                        id integer PRIMARY KEY AUTOINCREMENT,
                                        question text NOT NULL,
                                        answer_1 text NOT NULL,
                                        answer_2 text NOT NULL,
                                        answer_3 text NOT NULL,
                                        answer_4 text NOT NULL
                                    ) """

insert_question_table = """ INSERT INTO questions(question,answer_1,answer_2,answer_3,answer_4)
                            VALUES(?,?,?,?,?)
                        """

question_list = {
                    "You’re really busy at work and a colleague is telling you their life story and personal woes. You:": ['Don’t dare to interrupt them', 'Think it’s more important to give them some of your time; work can wait', 'Listen, but with only with half an ear', 'Interrupt and explain that you are really busy at the moment'],
                    "You’ve been sitting in the doctor’s waiting room for more than 25 minutes. You: ":['Look at your watch every two minutes', 'Bubble with inner anger, but keep quiet', 'Explain to other equally impatient people in the room that the doctor is always running late', 'Complain in a loud voice, while tapping your foot impatiently'],
                    "You’re having an animated discussion with a colleague regarding a project that you’re in charge of. You:":['Don’t dare contradict them', 'Think that they are obviously right', 'Defend your own point of view, tooth and nail', 'Continuously interrupt your colleague'],
                    "You are taking part in a guided tour of a museum. You:":['Are a bit too far towards the back so don’t really hear what the guide is saying', 'Follow the group without question', 'Make sure that everyone is able to hear properly', 'Are right up the front, adding your own comments in a loud voice']
                 }

select_question = """select * from questions where id==?"""

drop_table = """Drop table if exists questions"""

@app.route('/', methods=['GET', 'POST'])
def main():
    return render_template("personality_home.html")

@app.route('/finish/<personality_type>', methods=['GET', 'POST'])
def finish(personality_type):
    return render_template("finish.html", personality_prediction = "Your have "+personality_type+" personality.")


@app.route('/step/<int:step>', methods=['GET', 'POST'])
def step(step):

    db_conn = create_connection()
    question_1 = execute_db(db_conn, select_question, [step])
    question_list = [item for tup in question_1 for item in tup]
    question = {
        question_list[1]: [question_list[2], question_list[3], question_list[4], question_list[5]],
    }
    if request.method == 'POST':
        # Save form data to session
        session['step{}'.format(step)] = request.form.get("group")
        
        if step < total_question:
            # Redirect to next step
            return redirect(url_for('step', step=step+1))
        else:
            # Redirect to finish
            # get answers of all the questions
            input = []
            for i in range(1,total_question+1):
                input.append(int(session['step{}'.format(i)]))

            if len(input) == total_question:
                prediction = ml_model.predict([input])

            personality = "Extrovert" if prediction[0]==1 else "Introvert"
            return redirect(url_for('finish', personality_type = personality))

    return render_template('questions.html', question_dict = question, step = step)


if __name__=='__main__':

    db_conn = create_connection()
    #drop the data table if exist.
    execute_db(db_conn, drop_table)
    execute_db(db_conn, create_question_table)

    # fill the dummy data
    for question, answers in question_list.items():
        answers.insert(0, question)
        execute_db(db_conn, insert_question_table, answers)
    total_question = (execute_db(db_conn, "select MAX(id) from questions"))[0][0]
    app.run(debug=True)
    db_conn.close()