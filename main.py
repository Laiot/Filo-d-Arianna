#!/usr/bin/python

# Copyright (c) 2019 Politecnico di Milano [author: Giovanni Agosta]

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__doc__ = '''This (simple) web application serves gamebook-style navigable stories from the book/ folder, and proposes a configurable questionnaire at the end of the story.
The questionnaire data are stored in a ZODB database.

Bug reports to agosta@acm.org
'''

from flask import Flask, request, redirect, send_from_directory,render_template
import logging
from string import Template
import pydot
import networkx as nx
from uuid import uuid4
from glob import glob
from urllib.request import urlopen
from flask_security import Security, login_required, SQLAlchemySessionUserDatastore
from database import db_session, init_db
from models import User, Role,Survey, Keys
from flask_security.forms import RegisterForm, ChangePasswordForm
from flask_security.utils import hash_password
from flask_login import current_user
from wtforms import Form, DateField, TextAreaField, validators
from datetime import date
from secrets import token_hex


app = Flask(__name__, static_url_path='')
# random key generated by the system
app.config['SECRET_KEY'] = 'be14e1c905544a6eaf35c7637bfda48a'
app.config['SECURITY_REGISTERABLE'] = False
app.config['SECURITY_CHANGEABLE']=False
app.config['SECURITY_PASSWORD_SALT']= '3d83451fa9d5450290e0dfc8513c9f54'
app.config['SECURITY_SEND_REGISTER_EMAIL']=False
app.config['SECURITY_REGISTER_URL'] = '/register'
app.config['SECURITY_LOGIN_URL']='/admin'
app.config['SECURITY_POST_LOGIN_VIEW']='/admin/home'
app.config['SECURITY_LOGIN_USER_TEMPLATE']='login.html'
app.config['SECURITY_MSG_INVALID_EMAIL_ADDRESS']=('Mail  non corretta','error')
app.config['SECURITY_MSG_INVALID_PASSWORD']=('Password non corretta','error')
app.config['SECURITY_MSG_EMAIL_ALREADY_ASSOCIATED']=('Mail già registrata, controlla nel pannello laterale','error')
app.config['SECURITY_MSG_RETYPE_PASSWORD_MISMATCH']=('Le password inserite non coincidono','error')
app.config['SECURITY_MSG_PASSWORD_INVALID_LENGTH']=('La password non può essere più corta di 6 caratteri','error')


init_db() #check if db is empty
user_datastore = SQLAlchemySessionUserDatastore(db_session,User, Role) #create user manager for store and security
security = Security(app, user_datastore)
my_id = uuid4()#generation of unique session identifier
classtoken='' #identificativo di classe

#url per generazione tinyurl (da modificare in produzione)
urlsurvey="http://127.0.0.1:5000/index?token="
urledu="http://127.0.0.1:5000/edu?token="



# Configure logging
logging.basicConfig(filename='error.log', level=logging.DEBUG)
app.debug = True
app.logger.debug(app.root_path)
app.logger.debug(app.instance_path)
app.logger.debug(app.static_url_path)


# Setup page template
with open(app.root_path + '/templates/page.html') as fin:
    template_string = fin.read()
template_page = Template(template_string)


# Load books from books/
def load_book(path):
    '''Carica uno dei libri'''
    with open(path + '/graph.dot') as fin:
        data = fin.read()
    dotg = pydot.dot_parser.parse_dot_data(data)[0]
    nxg = nx.DiGraph(nx.drawing.nx_pydot.from_pydot(dotg))
    sources = [n for n in nxg.nodes if len(set(nxg.predecessors(n))) == 0]
    return dotg, nxg, sources[0]


books_directory = {}


def load_books():
    '''Carica tutti i libri trovati in books/'''
    books = glob('books/*')
    for b in books:
        if 'README.txt' in b: continue
        with open(b + '/title.txt', encoding="utf-8") as title_file:
            booktitle = title_file.read()
        try:
            with open(b + '/abstract.txt', encoding="utf-8") as abs_file:
                abstract = abs_file.read()
        except Exception:
            abstract = 'Un libro-gioco'
        dot, g, s = load_book(b)
        books_directory[b] = booktitle, dot, g, s, abstract


# setup the books
load_books()


class keyForm(Form):
    date = DateField('Data di fine validità:', default=date.today)
    description = TextAreaField('Descrizione', [validators.optional(), validators.length(max=500)])



# Key generation page
@app.route('/admin/keys', methods=['GET', 'POST'])
@login_required
def key():
    user = current_user._get_current_object()
    keys = Keys.query.all()
    error=''
    generated='false'
    if request.method == 'GET':
        keyform = keyForm()
        return render_template('key.html', user=user, keys=keys, keyform=keyform,generated=generated)
    else:
        keyform = keyForm(request.form)
        if keyform.date.data > date.today():
            error=""
            key=Keys()
            key.expiration=keyform.date.data
            key.token=token_hex(16)
            key.description=keyform.description.data
            response = urlopen("http://tinyurl.com/api-create.php?url=" + urlsurvey + key.token)
            key.urlsurvey=response.read().decode('utf-8')
            response2 = urlopen("http://tinyurl.com/api-create.php?url=" + urledu + key.token);
            key.urledu= response2.read().decode('utf-8')

            user_datastore.put(key)
            db_session.commit()
            generated=key.token
            keyform = keyForm()
        else:
            error="Data inserita non valida, validità minima: 1 giorno"
        keys = Keys.query.all()
        return render_template('key.html', user=user, keys=keys, keyform=keyform, error=error,generated=generated)



@app.route('/admin/changePassword', methods=['GET', 'POST'])
@login_required
def change():
    changed='false'
    user = current_user._get_current_object()
    change_form=ChangePasswordForm()
    if request.method == 'GET':
        return render_template('change.html', user=user, change_form=change_form, changed=changed)
    else:
        if change_form.validate_on_submit() or change_form.validate():

            user.password=hash_password(change_form.new_password.data)
            user_datastore.put(user)
            db_session.commit()
            changed = 'true'
        return render_template('change.html', user=user, change_form=change_form, changed=changed)

# Admin page
@app.route('/admin/home')
@login_required
def admin():
    user = current_user._get_current_object()
    return render_template('admin.html' ,user=user)

# New user page
@app.route('/admin/users',methods=['GET', 'POST'])
@login_required
def users():
    user = current_user._get_current_object()
    registered='false'
    register_form = RegisterForm()
    if request.method == 'GET':
        users = User.query.all()
        return render_template('users.html',  user=user, users=users, register_user_form=register_form,registered=registered)
    else:
        if register_form.validate_on_submit() or register_form.validate():
            user = User()
            register_form.populate_obj(user)
            user_datastore.create_user(email=user.email,password=hash_password(user.password))
            db_session.commit()
            registered='true'
        else:
            visible='block'
        users = User.query.all()
        return render_template('users.html', user=user, users=users, register_user_form=register_form,registered=registered)

@app.route('/admin/books')
@login_required
def books():
    user = current_user._get_current_object()
    return render_template('books.html', user=user)


# Dynamic web pages
@app.route('/')
@app.route('/index')
def index():
    data=dict(request.args)
    try:
         global classtoken
         classtoken = data['token']
    except KeyError:
        classtoken=''



    '''Pagina principale; offre la lettura dei libri oppure la possibilita' di scaricare i pdf'''
    with open(app.root_path + '/templates/intro.html', encoding="utf-8") as fin:
        base_content = fin.read()
    mapping = {
        'title': 'Storie dal labirinto',
        'content': base_content,
    }
    s = Template('''	<h1><a href="game?path=${link}&title=${title}">${title}</a></h1>
	<p>${text}</p>
	<h3><a href="game?path=${link}&title=${title}">Leggi il libro</a></h3>
	<h3><a href="libro?path=${link}">Scarica il libro</a></h3>
	''')

    for b in books_directory:
        booktitle = books_directory[b][0]
        text = books_directory[b][-1]
        m = {
            'link': b,
            'title': booktitle,
            'text': text,
        }
        mapping['content'] += s.substitute(m) + '\n'
    return template_page.substitute(mapping)


@app.route('/questionario')
def questionario():
    '''Questionario di valutazione; viene presentato dopo la lettura di uno dei libri'''
    mapping = {'title': 'Questionario'}
    data = dict(request.args)
    try:
        path = data['path']
        history = data['history']
    except KeyError:
        path = 'NA'
        history = 'NA'

    with open(app.root_path + '/templates/quest.html') as fin:
        template_string = fin.read()
    template_quest = Template(template_string)
    '''di seguito la lettura da path relativo al libro del questionario'''
    package = path.replace("/", ".") + ".quest"


    name = 'scaled_questions, binary_questions, scaled_question_template, binary_question_template'

    try:
        _temp = __import__(package, globals(), locals(), [name], 0)
        scaled_questions = _temp.scaled_questions
        binary_questions = _temp.binary_questions
        scaled_question_template = _temp.scaled_question_template
        binary_question_template = _temp.binary_question_template
    except ImportError as error:
        from quest import scaled_questions, binary_questions, scaled_question_template, binary_question_template

    scaled_questions_text = '\n'.join(
        [Template(scaled_question_template).substitute({'id': k, 'title': v}) for k, v in scaled_questions.items()])
    binary_questions_text = '\n'.join(
        [Template(binary_question_template).substitute({'id': k, 'title': v}) for k, v in binary_questions.items()])

    mapping['content'] = template_quest.substitute(
        {'path': path,
         'history': history,
         'tag': my_id,
         'scaled_questions': scaled_questions_text,
         'binary_questions': binary_questions_text}
    )
    return template_page.substitute(mapping)


@app.route('/store')
def store():

    '''Salva i dati del questionario nel db'''

    # Set up data to store
    data = dict(request.args)
    type='POST'
    age=None
    if data.get('history')=='NA':
        type='PRE'
    if data.get('age')!='':
        age=data.put('age')

    survey=Survey(data.get('tag'),classtoken, type, data.get('path'),data.get('history'),data.get('gender'),age,data.get('residence'),data.get('q1'),data.get('q2'),data.get('q3'),data.get('q4'),data.get('q5'),data.get('q6'),data.get('q7'),data.get('q8'),data.get('q9'),data.get('freetext'))
    db_session.add(survey)
    db_session.commit()
    return render_template('credits.html', type=type, path=data.get('path'))


@app.route('/libro')
def libro():
    data = dict(request.args)
    path = data['path']
    return send_from_directory(path, 'book.pdf')


link = Template('''
	<span class="content">
		<a href="game?path=$path&title=$booktitle&node=$node&history=$history">$label</a>
	</span>
''')

link_quest = Template('''
	<div id="content">
		<h1><a href="questionario?&path=$path&history=$history">Rispondi al questionario</a></h1>
	</div>
''')

arrow = '''
	<div class="arrow"><img src="images/singlearrow.png" alt="<->" height="17"></div>
'''


@app.route('/game')
def game():
    data = dict(request.args)
    path = data['path']
    '''booktitle = data['title']'''
    try:
        node = data['node']
        history = data['history']
    except KeyError:
        node = None
        history = ''
    booktitle, dot, g, s, abstract = books_directory[path]
    if not node: node = s
    next = list(g.successors(node))
    mapping = {
        'title': booktitle,
        'content': """			<h3>${name}</h3>
	<div id="content">
	${content}
	</div>
	""",
    }
    label = eval(dot.get_node(node)[0].get_attributes()['label'])
    try:
        with open(path + '/' + node + '.html', encoding="utf-8") as fin:
            content = fin.read()
            content = content.replace("\xe9", "&eacute;")
            content = content.replace("\xe0", "&agrave;")
            content = content.replace("\xc8", "&Egrave;")
            content = content.replace("\xf9", "&ugrave;")
            content = content.replace("\xe8", "&egrave;")
            content = content.replace("\xf2", "&ograve;")
            content = content.replace("\xec", "&igrave;")
    except Exception as e:
        content = label
    mapping['content'] = Template(mapping['content']).substitute(
        {'name': label, 'content': content})
    m = {
        'path': path,
        'booktitle': booktitle,
        'history': history + '.' + node,
    }
    if len(next): mapping['content'] = mapping['content']
    for n in next:
        label = eval(dot.get_node(n)[0].get_attributes()['label'])
        m['label'] = label
        m['node'] = n
        link_string = link.substitute(m)
        mapping['content'] =  mapping['content'] + '<div id="link">' + arrow + link_string + '</div>'
        if n != next[-1]: mapping['content'] = mapping['content']
    if not len(next):
        link_string = link_quest.substitute(m)
        mapping['content'] = mapping['content'] + link_string
    else:
        mapping['content'] = mapping['content']
    return template_page.substitute(mapping)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


if __name__ == '__main__':
    app.run(host='127.0.0.1',port=5000, debug= True)
