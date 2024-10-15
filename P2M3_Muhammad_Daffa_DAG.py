'''
=================================================
Milestone 3

Nama  : Muhammad Daffa
Batch : FTDS-007-BSD

The program is built to perform ETL system, which will include loading data from PostgreSQL, Cleaning the 
loaded dataset, and export it to ElasticSearch. Data set is about the sales of a Store from 2015 to 2018.
=================================================
'''


# Import Libraries
import datetime as dt
from datetime import timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

import pandas as pd
import psycopg2 as db
from elasticsearch import Elasticsearch



# Define Function for DAG

def queryPostgresql():
    '''
    This function is a Fetching Data function. It will connect to PostgreSQL and will
    import data from the airflow database.
    '''

    # Connecting with database airflow
    conn_string = "dbname='airflow' host='postgres' user='airflow' password='airflow'"
    conn=db.connect(conn_string)

    # Read file from the database and create it as dataframe
    df=pd.read_sql("select * from table_m3",conn)

    # Export dataframe as csv for further process
    df.to_csv('/opt/airflow/dags/P2M3_Muhammad_Daffa_Data_Raw.csv')
    print("-------Data Saved------")

def dataCleaning():
    '''
    This function is the cleaning function. The objective is to clean the fetched data from 
    PostgreSQL, including dropping duplicates, lower case column name, remove non letter,
    convert space to underscore, whitespace removal, and handling missing value
    '''

    # Creating Dataframe to read the raw data
    df_clean = pd.read_csv('/opt/airflow/dags/P2M3_Muhammad_Daffa_Data_Raw.csv', index_col = 0)

    # Dropping duplicates
    df_clean.drop_duplicates(inplace=True)

    # Lower case
    df_clean.columns = df_clean.columns.str.lower()

    # Convert space to underscore
    df_clean.columns = df_clean.columns.str.replace(' ', '_')

    # Whitespace removal
    df_clean.columns = [col.strip() for col in df_clean.columns]

    # Handle missing values -> Missing values is where the state is Vermont, replace the missing value with actual postal code
    df_clean.fillna('05408', inplace = True)

    # Convert shipping date and order date column to datetime datatype
    df_clean['ship_date'] = pd.to_datetime(df_clean['ship_date'], format='%d/%m/%Y', errors='coerce')
    df_clean['order_date'] = pd.to_datetime(df_clean['order_date'], format='%d/%m/%Y', errors='coerce')

    # Change postal code column to integer type
    df_clean['postal_code'] = df_clean['postal_code'].astype(int)

    # Save cleaned data to csv
    df_clean.to_csv('/opt/airflow/dags/P2M3_Muhammad_Daffa_Data_Clean.csv', index=False)


def insertElasticsearch():
    # Connecting elasticsearch
    es = Elasticsearch("http://elasticsearch:9200") 

    # Read the cleaned data
    df_final = pd.read_csv('/opt/airflow/dags/P2M3_Muhammad_Daffa_Data_Clean.csv')


    for i,r in df_final.iterrows():
        '''
        This looping function to covert the document into json type,
        for it to be compatible with elastic search
        '''
        doc=r.to_json()
        es.index(index="frompostgresql",doc_type="doc",body=doc)	# Creating new index 'frompostgresql' to elasticsearch



with DAG('Dag_Project_M3',
        start_date = dt.datetime(2024, 9, 12), # Define Start Date
        schedule_interval='30 23 * * *'        # Schedule the DAG for 6.30 WIB
         ) as dag:
    '''
    This function to create DAG to perform 3 main tasks, which are data cleaning, fetching data from PostgreSQL, 
    and inserting cleaned data to Elastic Search
    '''
    # Data Cleaning Task
    dataCleaning = PythonOperator(task_id='DataCleaning',
                                 python_callable=dataCleaning)
    
    # Fetching Data from PostgreSQL Task
    fetchData = PythonOperator(task_id='QueryPostgreSQL',
                                 python_callable=queryPostgresql)
    
    # Inserting Data to ElasticSearch Task
    insertData = PythonOperator(task_id='InsertDataElasticsearch',
                                 python_callable=insertElasticsearch)



fetchData >> dataCleaning >> insertData