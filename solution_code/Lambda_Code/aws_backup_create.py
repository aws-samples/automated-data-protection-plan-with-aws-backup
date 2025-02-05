# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3
from botocore.vendored import requests

regions_array = ["us-east-1", "us-east-2"]

# Main Lambda Handler Block

def lambda_handler(event, context):
    print(event)
    print(event["ABSName"])
    ABSName = event["ABSName"]
    AccountId = event["AccountId"]
    sts_connection = boto3.client('sts')
    acct_b = sts_connection.assume_role(
        RoleArn=f"arn:aws:iam::{AccountId}:role/Xacnt_Backup_Role",
        RoleSessionName="cross_acct_lambda"
    )

    ACCESS_KEY = acct_b['Credentials']['AccessKeyId']
    SECRET_KEY = acct_b['Credentials']['SecretAccessKey']
    SESSION_TOKEN = acct_b['Credentials']['SessionToken']

    # Region 1 (us-east-1) crossaccount access

    calling_account_session = boto3.Session(region_name='us-east-1', aws_access_key_id=ACCESS_KEY,
                                      aws_secret_access_key=SECRET_KEY,
                                      aws_session_token=SESSION_TOKEN)

    kms_client = calling_account_session.client('kms')
    backup_client = calling_account_session.client('backup')


    # Region 2 (us-east-2) crossaccount access

    us_east_2_session = boto3.Session(region_name='us-east-2', aws_access_key_id=ACCESS_KEY,
                                      aws_secret_access_key=SECRET_KEY,
                                      aws_session_token=SESSION_TOKEN)

    kms_client_us_east_2 = us_east_2_session.client('kms')
    backup_client_us_east_2 = us_east_2_session.client('backup')

   # Methods to call

    response = create_backup_vault(
        ABSName, backup_client, kms_client, 'us-east-1')
    response = create_backup_vault(
        ABSName, backup_client_us_east_2, kms_client_us_east_2, 'us-east-2')

    response = create_backup_plan(ABSName, AccountId, backup_client, calling_account_session)

    response = create_backup_selection(ABSName, AccountId, backup_client)

    return {
        'statusCode': 200,
        'body': json.dumps('Default Vault created in us-east-1, us-east-2. Backup plan and selection created!')
    }
    # return response.BackupPlanArn

# Create Backup Plan method

def create_backup_plan(ABSName, AccountId, client, calling_account_session):
    """
    Creates default backup plan with default values
    """
    BackupPlanName = ABSName+'-RDS-BackupPlan-Default'
    VaultName = ABSName + '-Vault'
    RuleName = ABSName+'-RDS-BackupRule-Default'
    DestinationBackupVaultArn = f"arn:aws:backup:us-east-2:{AccountId}:backup-vault:"+VaultName
    output = get_ssm_data("/backupprocess/backupplan", calling_account_session)
    print(f'output: {output}')
    backupplan = json.loads(output)[0]
    print('plan before', backupplan)
    backupplantags = json.loads(output)[1]
    print('tags before', backupplantags)
    backupplan["BackupPlanName"] = BackupPlanName #custom
    backupplan["Rules"][0]["RuleName"] = RuleName #custom
    backupplan["Rules"][0]["TargetBackupVaultName"] = VaultName
    backupplan["Rules"][0]["CopyActions"][0]["DestinationBackupVaultArn"] = DestinationBackupVaultArn
    backupplan["Rules"][0]["ScheduleExpression"] = "cron(0 * * * ? *)"  # Set the backup frequency to every 1 hour
    print('plan after', backupplan)
    backupplantags["ABS"] = ABSName
    print('tags after', backupplantags)
    response = client.create_backup_plan(
        BackupPlan= backupplan,
        BackupPlanTags=backupplantags
    )

# Get Backup Plan Id method

def get_plan_id(ABSName, client):
    PlanName = ABSName+'-RDS-BackupPlan-Default'
    planList = client.list_backup_plans()
    plans = (planList['BackupPlansList'])
    for plan in plans:
            if plan['BackupPlanName']==PlanName:
                print(plan)
                planID=plan['BackupPlanId']
                break
    return (planID)

# Create Backup Selection method


def create_backup_selection(ABSName, AccountId, client):
    planID = get_plan_id(ABSName, client)
    print(f"HERE {planID}")
    IamRoleArn = f"arn:aws:iam::{AccountId}:role/AWSBackup-Custom"
    SelectionName = ABSName + "-RDS-BackupSelection-Default"
    response = client.create_backup_selection(
    BackupPlanId=planID,
    BackupSelection={
        'SelectionName': SelectionName,
        'IamRoleArn': IamRoleArn,
        'Resources': [
            'arn:aws:rds:*:*:db:*', 'arn:aws:rds:*:*:cluster:*'
        ],
        'Conditions': {
            "StringEquals": [
                    {
                'ConditionKey': 'aws:ResourceTag/ABS',
                'ConditionValue': ABSName
                }
                ]
            }})

    print(response)

# Create Backup Vault method
    
def create_backup_vault(ABSName, backup_client, kms_client, region):
    kms_alias = ABSName+ "-key"
    backupVaultName = ABSName + "-Vault"
    key_alias_arn, alias_name, taeget_key_id = get_arn_by_alias(
        ABSName, region, kms_client)
    key_arn = get_key_arn_by_id(taeget_key_id, region, kms_client)
    print("This is the:", key_arn)
    response = backup_client.create_backup_vault(BackupVaultName=backupVaultName,
                    BackupVaultTags={
                        'ABS': ABSName
                    },
                    EncryptionKeyArn=key_arn
                )
    return (response)

# Get KMS KEY ARN using KMS KEY ALIAS


def get_arn_by_alias(ABSName, region_name, client):
    list_keys = client.list_keys()
    alias_name = ABSName + '-key'
    print(list_keys)
    key_found = False
    key_aliases = client.list_aliases()
    if key_aliases:
        print(f"Response: {key_aliases}")
        for element in key_aliases["Aliases"]:
            if element['AliasName'] == f"alias/{alias_name}":
                key_found = True
                print(f"Found kms id using kms alias {alias_name}")
                return (element['AliasArn'], element['AliasName'], element['TargetKeyId'])
        if not key_found:
            print(f"KMS key:{alias_name} not found")
            return ("", "", "")


def get_key_arn_by_id(id, region, kms_client):
    done = False
    key_arn = ""
    key_aliases = kms_client.list_keys()
    while not done:
        if key_aliases:
            print(f"key arn Response: {key_aliases}")
            for element in key_aliases["Keys"]:
                if element['KeyId'] == id:
                    done = True
                    key_arn = element['KeyArn']
                    break
        if key_aliases['Truncated']:
            marker = key_aliases['NextMarker']
            key_aliases = kms_client.list_keys(Marker=marker)
        else:
            done = True
    return key_arn


def get_ssm_data(parameter_name, calling_account_session):
    client = calling_account_session.client("ssm")
    parameter = client.get_parameter(Name=parameter_name)
    print(parameter)
    return parameter ['Parameter']['Value']