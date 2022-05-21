# Instructions 

## Code Formatting

We use black for code styling and styling

run `black filename` 

Note - Do style and reformat the code before pushing

## Steps to run the project

- Clone repository.

- Install requirements using
```shell
pip install -r requirements.txt
```

- Make migrations 
```shell
python3 manage.py makemigrations
```
- Run migrations
```shell
python3 manage.py migrate
```

- Start server
```shell
python3 manage.py runserver
```

