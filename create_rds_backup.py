import os
import boto3
import json
import subprocess
from datetime import date
import logging

logging.basicConfig(level=logging.INFO, force=True)
logger = logging.getLogger()

class RDSBackup:
    def __init__(self, secret_name, region, bucket, database):
        self.secret_name = secret_name
        self.region = region
        self.database = database
        self.bucket = bucket
        self.session = boto3.session.Session()
        self.secrets_client = self.session.client(
            service_name='secretsmanager',
            region_name=self.region
        )

        # moves required scripts to /tmp in order to run within lambda
        subprocess.check_call(["cp ./backup.sh /tmp/backup.sh && chmod 755 /tmp/backup.sh"], shell=True)
        subprocess.check_call(["cp ./bin/mysqldump /tmp/mysqldump && chmod 755 /tmp/mysqldump"], shell=True)

    def _get_secret(self):
        """
        private helper method for retrieving credentials from Secret Manager
        """
        creds = json.loads(self.secrets_client.get_secret_value(SecretId=self.secret_name)['SecretString'])

        return {
            'host': creds['rds_host'],
            'username': creds['username'],
            'password': creds['password']
        }

    def _upload_to_s3(self, file):
        """
        private helper method for uploading to s3
        """
        s3 = boto3.resource(
            's3',
            self.region
        )

        s3_response = s3.meta.client.upload_file('/tmp/backup.sql', self.bucket, file)
        logger.info(s3_response)

    def create_backup(self):
        try:
            rds_credentials = self._get_secret()
            filename = "{}-{}.sql".format(self.database, date.today())

            # calls the backup script which executes mysqldump
            subprocess.check_call(
                [
                    "/tmp/backup.sh",
                    rds_credentials['host'],
                    rds_credentials['username'],
                    rds_credentials['password'],
                    self.database
                ]
            )
            self._upload_to_s3(filename)

            return True
        except:
            return False


def main(event, context):
    # read environment variables from lambda
    secret_name = os.environ['secret_name']
    region = os.environ['region']
    bucket_name = os.environ['bucket']
    database = os.environ['database']

    # initiate a new instance of RDSBackup
    rds_backup_client = RDSBackup(
        secret_name=secret_name,
        region=region,
        bucket=bucket_name,
        database=database
    )

    # create backup / upload to s3 and output status
    if rds_backup_client.create_backup():
        logger.info("Backup was successful.")
    else:
        logger.info("Backup failed.")
