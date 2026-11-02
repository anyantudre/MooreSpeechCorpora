install:
	pip install --upgrade pip &&\
		pip install -r requirements.txt

test:
	python app.py

format:
	#black *.py

lint:
	#pylint --disable=R,C *.py

all: install lint test format