__author__ = 'Rand01ph'


import os
from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.bootstrap import Bootstrap
from flask.ext.moment import Moment
from flask.ext.login import UserMixin, LoginManager, login_required, login_user, logout_user
from flask.ext.wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import Required, Length, Email
from flask import Flask, request, session, redirect, url_for, render_template, flash


basedir = os.path.abspath(os.path.dirname(__file__))


app = Flask(__name__)
moment = Moment(app)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.session_protection = 'basic'
login_manager.login_view = 'login'


'''程序配置'''
app.config.update(dict(
    SQLALCHEMY_DATABASE_URI ='sqlite:///' + os.path.join(basedir, 'blog.sqlite'),
    SECRET_KEY='not a password',
    DEBUG=True,
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True,
))



'''数据库模型'''
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
		return '<User %r>' % self.username


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True)
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    def __repr__(self):
        return '<Post %r>' % self.title


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    reply = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    def __repr__(self):
        return '<Comment %r>' % self.reply


'''表单定义'''
class LoginForm(Form):
	username = StringField(u'用户名', validators=[Required(), Length(1, 64)])
	email = StringField('Email', validators=[Required(), Length(1, 64),
	                                         Email()])
	password = PasswordField(u'密码', validators=[Required()])
	remember_me = BooleanField(u'记住我')
	submit = SubmitField(u'登录')

class PostForm(Form):
	title = StringField(u'标题', validators=[Required()])
	text = TextAreaField(u'内容', validators=[Required()])
	submit = SubmitField(u'提交')



'''博客首页'''
@app.route('/')
def index():
	posts = Post.query.order_by(Post.timestamp.desc()).all()
	return render_template('index.html', posts=posts)


'''博文页面'''
@app.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    comments = post.comments.all()
    if request.method == 'POST':
        addcomments = Comment(reply=request.form['reply'], post=post)
        db.session.add(addcomments)
        return redirect(url_for('index'))
    return render_template('post.html', post=post, comments=comments)


'''编写博文'''
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_entry():
    if request.method == 'POST':
        post=Post(title=request.form['title'], text=request.form['text'], timestamp=datetime.now())
        db.session.add(post)
        flash('New entry was successfully posted')
        return redirect(url_for('index'))
    return render_template('add.html')


'''删除博文'''
@app.route('/delete/<int:id>')
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    flash(u'博客已被删除')
    return redirect(url_for('index'))


'''登录'''
@app.route('/login', methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(username=form.username.data).first()
		if user is not None:
			login_user(user, form.remember_me.data)
			return render_template(request.args.get('next') or url_for('index'))
		flash(u'用户名错误')
	return render_template('login.html', form=form)


'''登出'''
@app.route('/logout')
@login_required
def logout():
	logout_user()
    flash(u'登出成功')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()