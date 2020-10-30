import json
import boto3
import botocore
import os
import requests
import subprocess
from operator import itemgetter
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def generate_response(status_code, message):
    """
    Generate response.
    """

    return {
                    "statusCode": status_code,
                    "body": json.dumps(message)
           }


def download_from_s3():
    """
    Download a file from AWS S3 bucket.
    """

    BUCKET_NAME = os.environ['BUCKET_NAME']
    KEY = os.environ['BUCKET_FOLDER_PATH']
    BUCKET_FILE_NAME = os.environ['BUCKET_FILE_NAME']
    DEST_FILE = '/tmp/{}'.format(BUCKET_FILE_NAME)

    s3 = boto3.client('s3')

    try:
        s3.download_file(BUCKET_NAME, KEY, DEST_FILE)

        return DEST_FILE
    except botocore.exceptions.ClientError as err:
        if e.response['Error']['Code'] == "404":
            print(err)
            return generate_response(404, err)
        else:
            raise

def create_db(**opts):
    """
    Drop and create new clean database.
    """

    database, user, host, password, temp_database \
      = itemgetter('database', 'user', 'host', 'password', 'temp_database')(opts)

    try:
        con = psycopg2.connect(dbname=database, post="5432",
                               user=user, host=host,
                               password=password)
    except Exception as err:
        print(err)
        return generate_response(400, err)

    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()

    try:
        cur.execute("DROP DATABASE {} ;".format(temp_database))
    except Exception as err:
        print('DB does not exist, nothing to drop')

    cur.execute("CREATE DATABASE {} ;".format(temp_database))
    cur.execute("GRANT ALL PRIVILEGES ON DATABASE {} TO {} ;".format(temp_database, user))

def restore_postgres_db(**opts):
    """
    Restore postgres db from a file.
    """

    database, user, host, password, temp_database, sql_file \
      = itemgetter('database', 'user', 'host', 'password', 'temp_database', 'sql_file')(opts)

    try:
        process = subprocess.Popen(
            ['PGPASSWORD={}'.format(password),
             'psql',
             '--host={}'.format(host),
             '--port=5432',
             '--username={}'.format(user),
             '--dbname={}'.format(temp_database),
             '-f {}'.format(sql_file)],
            stdout=subprocess.PIPE
        )
        output = process.communicate()[0]
        if int(process.returncode) != 0:
            print('Command failed. Return code : {}'.format(process.returncode))

        return output
    except Exception as err:
        print("Issue with the db restore : {}".format(err))
        return generate_response(400, err)

def handler(event, context):
    """
    Respond to event fron S3 bucket file uploaded.
    """

    print("-=-=-= GOT EVENT -=-=-=-")
    print(event)

    DB_NAME = os.environ["POSTGRES_DB"]
    USER_NAME = os.environ["POSTGRES_USER"]
    HOST = os.environ["POSTGRES_HOST"]
    PASSWORD = os.environ["POSTGRES_PASSWORD"]
    TEMPLATE_DATABASE = os.environ["TEMPLATE_DB"]

    # download latest sql file from S3 and save it in temp dir
    DEST_FILE_PATH = download_from_s3()

    # clean database from previous data
    create_db(database=DB_NAME,
              user=USER_NAME,
              host=HOST,
              password=PASSWORD,
              temp_database=TEMPLATE_DATABASE)

    # restore database with newest sql file
    restore_postgres_db(database=DB_NAME,
                        user=USER_NAME, host=HOST,
                        password=PASSWORD,
                        temp_database=TEMPLATE_DATABASE,
                        sql_file=DEST_FILE_PATH)

    generate_response(200, "Updated database template for TeamCity in AWS RDS.")
