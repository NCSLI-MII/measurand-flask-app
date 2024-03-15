# measurand-flask-app
Flask application for MII metadata

In order to setup the test database, several resources are used to initialize the database.
* NCSLI MII Measurand Taxonomy
* M-Layer REST API
```
curl -X 'GET' 'https://dr49upesmsuw0.cloudfront.net/aspects' -H 'accept: application/json' -- output aspects.json 
curl -X 'GET' 'https://dr49upesmsuw0.cloudfront.net/scales' -H 'accept: application/json' -- output scales.json 
```
Updated resource files can be copied to
```
resources
```
## Getting started

* Create a working directory
* Create the conda environment
* For virtual environments, use [miniforge](https://github.com/conda-forge/miniforge)
```
conda create -n <environment_name> --file requirements.txt
```
* Update to the latest input data for the taxonomy and mlayer.
* Run the mappers.
* Load the data in memory
```
python dbinit.py -p builder.json -m
```
* Create a persistent database. See the builder.json for database path. The current location is in /tmp
```
/tmp/miiflask/miiflask.db
```
```
python dbinit.py -p builder.json -d
```
* Update database path in flask [config](./miiflask/flask/config.py) if changed in builder.json.
* To extract data from the KCDB and m-layer APIs, update the builder.json file.
```
use_api=true
```

### Running the flask application
Two modes have configurations for running the flask application. Before running the application export the Flask environment.
* Testing configuration runs an in-memory database that requires extracting and loading the data each time. 

```
export FLASK_ENV=testing
```

* The debug mode uses the database that was initialized from the dbinit.py script. Changes to the database will be persisted, so the user keep changes to the database.

```
export FLASK_ENV=development
```

``` 
cd miiflask/flask
flask run
```
* Go to the localhost on browser http://127.0.0.1/5000
* The administration view can be found at http://127.0.0.1/5000/admin
* For in-memory, you'll need to load some data. Go to http://127.0.0.1/5000/initialize

Below was a diagram of the database schema implemented as a flask [model](./miiflask/flask/model.py).

![Schema](./taxonomyschema.png)
