from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager
from flask_login import login_required
from flask_login import login_user, logout_user
from flask_login import current_user
from passwordhelper import PasswordHelper
import config 
import datetime
from bitlyhelper import BitlyHelper
from forms import RegistrationForm, LoginForm
from forms import CreateTableForm

if config.test:
    from mockdbhelper import MockDBHelper as DBHelper
else:
    from dbhelper import DBHelper

from user import User
DB = DBHelper()
PH = PasswordHelper()
BH = BitlyHelper()

app = Flask(__name__)
app.secret_key = 'tPXJY3G!37Qybz4QykV+h98yUxVQeEXf1Ao2C8upz+fGQXKsM'
login_manager = LoginManager(app)


@app.route("/")
def home():
    return render_template("home.html", loginform=LoginForm(), registrationform= RegistrationForm())

@app.route("/account")
@login_required
def account():
    tables = DB.get_tables(current_user.get_id())
    return render_template("account.html", createtableform=CreateTableForm(), tables=tables)

@login_manager.user_loader
def load_user(user_id):
    user_password = DB.get_user(user_id)
    if user_password:
        return User(user_id)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    now = datetime.datetime.now()
    requests = DB.get_requests(current_user.get_id())
    for req in requests:
        deltaseconds = (now - req['time']).seconds
        req['wait_mnutes'] = "{}.{}".format((deltaseconds/60),str(deltaseconds % 60).zfill(2))
    return render_template("dashboard.html", requests=requests)

@app.route("/register", methods=["POST"])
def register():
    form = RegistrationForm(request.form)
    if form.validate():
        if DB.get_user(form.email.data):
            form.email.errors.append("Email address already registered")
            return render_template('home.html', loginform=LoginForm(), registrationform=form,
                         onloadmessage="Registration successful. Please log in.")
        salt =PH.get_salt()
        hashed = PH.get_hash(form.password2.data + str(salt))
        DB.add_user(form.email.data, salt, hashed)
        return render_template("home.html", loginform=LoginForm(), registrationform=form)
    return render_template("home.html", loginform=LoginForm() ,registrationform=form)

@app.route("/account/createtable", methods=["POST"])
@login_required
def account_createtable():
    form = CreateTableForm(request.form)
    if form.validate():
        tableid = DB.add_table(form.tablenumber.data, current_user.get_id())
        new_url = BH.shorthen_url(config.base_url+ "newrequest/" + str(tableid))
        DB.update_table(tableid, new_url)
        return redirect(url_for('account'))
    return render_template("account.html", createtableform=form,
        tables=DB.get_tables(current_user.get_id()))

@app.route("/account/deletetable")
@login_required
def account_deletetable():
    tableid = request.args.get("tableid")
    DB.delete_table(tableid)
    return redirect(url_for('account'))

@app.route("/newrequest/<tid>")
def new_request(tid):
    DB.add_request(tid, datetime.datetime.now())
    return "You request has been logged and a waiter will be with you shortly"

@app.route("/dashboard/resolve")
@login_required
def dashboard_resolve():
    request_id = request.args.get("request_id")
    DB.delete_request(request_id)
    return redirect(url_for('dashboard'))

@app.route("/login", methods=["POST"])
def login():
    form = LoginForm(request.form)
    if form.validate():
        store_user = DB.get_user(form.loginemail.data)
        if store_user and PH.validate_password(form.loginemail.data,
            store_user['salt'], store_user['hashed']):
            user = User(form.loginemail.data)
            login_user(user, remember=True)
            return redirect(url_for('account'))
        form.loginemail.errors.append("Email or password invalid")
    return render_template("home.html", loginform=form,
        registrationform=RegistrationForm())

if __name__=="__main__":
    app.run(port=5005, debug=True)