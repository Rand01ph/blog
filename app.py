# coding=utf-8

import os
from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.bootstrap import Bootstrap
from flask.ext.moment import Moment
from flask.ext.login import UserMixin, LoginManager, login_required, login_user, logout_user
from flask.ext.wtf import Form
from flask.ext.pagedown import PageDown
from flask.ext.pagedown.fields import PageDownField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import Required, Length, Email
from markdown import markdown
import bleach
from flask import Flask, request, session, redirect, url_for, render_template, flash


basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
moment = Moment(app)
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.session_protection = 'basic'
login_manager.login_view = 'login'
pagedown = PageDown(app)

'''程序配置'''
app.config.update(dict(
	SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(basedir, 'blog.sqlite'),
	SECRET_KEY='not a password',
	DEBUG=True,
	SQLALCHEMY_COMMIT_ON_TEARDOWN=True,
	PER_PAGE=10
))

'''数据库模型'''


class User(UserMixin, db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(64), unique=True, index=True)
	password = db.Column(db.String(128))

	def __repr__(self):
		return '<User %r>' % self.username


@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))


class Post(db.Model):
	__tablename__ = 'posts'
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String, nullable=False)
	text = db.Column(db.Text, nullable=False)
	text_html = db.Column(db.Text)
	timestamp = db.Column(db.DateTime, index=True)
	comments = db.relationship('Comment', backref='post', lazy='dynamic')

	@staticmethod
	def on_changed_text(target, value, oldvalue, initiator):
		allowed_tags = ['a', 'addr', 'acronym', 'b', 'blockquote', 'code',
		                'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
		                'h1', 'h2', 'h3', 'p']
		target.text_html = bleach.linkify(bleach.clean(
			markdown(value, output_format='html'),
			tags=allowed_tags, strip=True))

	def __repr__(self):
		return '<Post %r>' % self.title


class Comment(db.Model):
	__tablename__ = 'comments'
	id = db.Column(db.Integer, primary_key=True)
	reply = db.Column(db.Text, nullable=False)
	post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

	def __repr__(self):
		return '<Comment %r>' % self.reply


db.event.listen(Post.text, 'set', Post.on_changed_text)

'''表单定义'''


class LoginForm(Form):
	username = StringField(u'用户名', validators=[Required(), Length(1, 64)])
	password = PasswordField(u'密码', validators=[Required()])
	remember_me = BooleanField(u'记住我')
	submit = SubmitField(u'登录')


class PostForm(Form):
	title = StringField(u'标题', validators=[Required()])
	text = PageDownField(u'内容', validators=[Required()])
	submit = SubmitField(u'提交')


'''博客首页'''


@app.route('/')
def index():
	page = request.args.get('page', 1, type=int)
	pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
		page, per_page=app.config['PER_PAGE'],
		error_out=False)
	posts = pagination.items
	return render_template('index.html', posts=posts)


'''博文页面'''


@app.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
	post = Post.query.get_or_404(id)
	comments = post.comments.all()
	if request.method == 'POST':
		addcomments = Comment(reply=request.form['reply'], posts=post)
		db.session.add(addcomments)
		return redirect(url_for('index'))
	return render_template('post.html', posts=[post], comments=comments)


'''编写博文'''


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
	form = PostForm()
	if form.validate_on_submit():
		post = Post(title=form.title.data,
		            text=form.text.data)
		db.session.add(post)
		return redirect(url_for('index'))
	return render_template('add.html', form=form)

'''编辑博文'''


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
	post = Post.query.get_or_404(id)
	form = PostForm()
	if form.validate_on_submit():
		post.title = form.title.data
		post.text = form.text.data
		db.session.add(post)
		flash('The post has been updated.')
		return redirect(url_for('post', id=post.id))
	form.title.data = post.title
	form.text.data = post.text
	return render_template('edit_post.html', form=form, id=post.id)


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
			return redirect(request.args.get('next') or url_for('index'))
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