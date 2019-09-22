from flask import Flask, request, render_template
from models import db

# app config
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/grocer'
db.init_app(app)

# app routes
@app.route('/')
def home():
	return render_template('show_all.html', items=items.query.all())


if __name__ == "__main__":
	app.run()
