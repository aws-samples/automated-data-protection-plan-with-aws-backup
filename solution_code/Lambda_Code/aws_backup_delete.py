# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import boto3

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

    ### Delete Backup Recovery Point ###

    response = delete_recovery_point(ABSName, backup_client)
    response = delete_recovery_point(ABSName, backup_client_us_east_2)

    ### Delete Backup Selection ###

    response = delete_backup_selection(ABSName, backup_client)

    ### Delete Backup Plan ###

    response = delete_backup_plan(ABSName, backup_client)


    ### Delete Backup Vault ####

    response = delete_backup_vault(ABSName, backup_client)
    response = delete_backup_vault(ABSName, backup_client_us_east_2)

    return {
        'statusCode' : 200,
        'body' : json.dumps("Default Vault deleted in us-east-1, us-east-2. Backup Plan and Selection deleted!")
    }

    # return response.BackupPlanArn

    ### Define Backup Recovery Point method

def delete_recovery_point(ABSName, backup_client):
    response = ""
    backupVaultName = ABSName + "-Vault"
    list_backup_vaults_response = backup_client.list_backup_vaults()
    if(len(list_backup_vaults_response['BackupVaultList'])>0):
        for backup_vault in list_backup_vaults_response['BackupVaultList']:
            if(backup_vault['BackupVaultName'] == backupVaultName):
                recovery_points_list = backup_client.list_recovery_points_by_backup_vault(
                    BackupVaultName=backupVaultName
                    )
                if len(recovery_points_list['RecoveryPoints'])>0:
                    for recovery_point in recovery_points_list['RecoveryPoints']:
                        recovery_point_arn = recovery_point['RecoveryPointArn']
                        response = backup_client.delete_recovery_point(
                            BackupVaultName=backupVaultName,
                            RecoveryPointArn=recovery_point_arn
                        )
    return response

    ### Define Delete Backup Vault method

def delete_backup_vault(ABSName, backup_client):
    response = ""
    backupVaultName = ABSName + "-Vault"
    list_backup_vaults_response = backup_client.list_backup_vaults()
    if(len(list_backup_vaults_response['BackupVaultList'])>0):
        for backup_vault in list_backup_vaults_response['BackupVaultList']:
            if(backup_vault['BackupVaultName'] == backupVaultName):
                response = backup_client.delete_backup_vault(BackupVaultName=backupVaultName)

    if(response == ""):
        print(f"No vaults with name {backupVaultName} found! skipping...")
    return(response)


    ### Define Default Backup Selection deletion method

def delete_backup_selection(ABSName, backup_client):
    response = ""
    backup_plan_name=ABSName + "-RDS-BackupPlan-Default"
    backup_plan_list_response = backup_client.list_backup_plans()
    if len(backup_plan_list_response['BackupPlansList']) >0:
        for backup_selection in backup_plan_list_response['BackupPlansList']:
            if backup_plan_name == backup_selection['BackupPlanName']:
                backup_selections_list_response = backup_client.list_backup_selections(
                    BackupPlanId=backup_selection['BackupPlanId']
                    )
                if(len(backup_selections_list_response['BackupSelectionsList'])>0):
                    for backup_selection in backup_selections_list_response['BackupSelectionsList']:
                        response = backup_client.delete_backup_selection(
                            BackupPlanId=backup_selection['BackupPlanId'],
                            SelectionId=backup_selection['SelectionId']
                            )
    return(response)

    ### Define Default Backup Plan deletion method

def delete_backup_plan(ABSName, backup_client):
    response = ""
    backup_plan_name=ABSName + "-RDS-BackupPlan-Default"
    backup_plan_list_response = backup_client.list_backup_plans()
    if len(backup_plan_list_response['BackupPlansList']) >0:
        for backup_selection in backup_plan_list_response['BackupPlansList']:
            if backup_plan_name == backup_selection['BackupPlanName']:
                response = backup_client.delete_backup_plan(
                    BackupPlanId=backup_selection['BackupPlanId']
                )
    return(response)
