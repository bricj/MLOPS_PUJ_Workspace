from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import mlflow
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import train_test_split
import os
import boto3
from botocore.config import Config
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score