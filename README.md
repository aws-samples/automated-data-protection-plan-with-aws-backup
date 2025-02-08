# AWS Backup Data Protection Plan

A solution for centralized backup management of RDS databases across multiple AWS accounts with enhanced security and cross-region replication capabilities. This project provides a streamlined approach to managing backup operations for data stored in Amazon RDS databases using AWS Backup and AWS Lambda. It enables centralized backup management across multiple AWS accounts, ensuring compliance, security, and automation.

## Solution Overview

This solution provides an automated approach to manage backup operations for RDS databases using AWS Backup service. It implements a multi-account strategy where a master account controls backup resources across target accounts, ensuring standardized backup policies while allowing for custom configurations.

### Key Features

- Centralized backup management across multiple AWS accounts
- Automated cross-region backup replication (us-east-1 to us-east-2)
- KMS encryption for enhanced security
- Tag-based resource selection
- Automated backup reporting and monitoring
- Compliance tracking through AWS Backup Audit Manager

## Prerequisites

- Two AWS Accounts:
  - Master Account: Permissions for AWS CloudFormation, Lambda, VPC, EC2, CloudWatch, IAM, and S3
  - Target Account: Permissions for AWS Backup, KMS, RDS, VPC, IAM, and EC2
- AWS CLI configured
- Basic knowledge of AWS services

## Components

- AWS Backup
- AWS Lambda
- AWS KMS (Multi-Region Keys)
- Amazon RDS
- AWS IAM
- AWS Systems Manager Parameter Store

## Architecture Diagram

![alt text](architecture_diagram.png)

## Solution Workflow

1.	The master account hosts Lambda function to create backup resources in the target account. 
2.	A JSON formatted input triggers the Backup Lambda using:
{
  "ABSName": "backup-blog",
  "AccountId": "xxxxxxxxxxxx"
}
3.	The Backup Lambda function contains the code to create the AWS Backup resources in the target account using the ‘ABSName’ and the intended target account ID as inputs. 
4.	The Backup Lambda’s execution role ‘backup-blog-LambdaExecutionRole’ assumes the role Xacnt_Backup_Role in the target account.
5.	In the target Account, Backup Lambda creates primary AWS Backup Vault in US-EAST-1 region. The vault uses a KMS multi-region key, which initially is created in the US-EAST-1 region and is replicated to the US-EAST-2 region.
6.	The Backup Lambda also creates secondary AWS Backup Vault in US-EAST-2 region using the replicated KMS multi region key for the application. 
7.	The Backup Lambda creates the default backup plan as per rules defined in AWS Systems Manager Parameter Store ‘/backupprocess/backupplan’
8.	The Backup Lambda also creates default backup selection.
9.	The RDS resource in the US-EAST-1 region with the tag ‘[ABS - backup-blog]’ will be tracked by the backup selection and initiates the backup job based on the configuration set in the backup plan 
10.	The successful backup job will result in a ‘recovery point’ stored in the respective vault and also is successful copied over to the US-EAST-2 region’s backup vault.

## IAM Roles

AWSBackup-Custom:-
Facilitates AWS Backup service operations, allowing RDS backup, encryption, and cross-region copy operations.

XacntBackupRole:-
Used by the master account’s Lambda function to perform backup operations across multiple AWS accounts.

## Deployment Steps

1.	Clone the Source Code Repository:
•	Clone the source code repository from the AWS Samples GitHub to your local machine.

```bash
git clone https://github.com/aws-samples/automated-data-protection-plan-with-aws-backup.git
cd automated-data-protection-plan-with-aws-backup
```

2.	Upload Lambda Function Zip Files:
•	Zip the python files with 'aws_backup_create.py.zip' and 'aws_backup_delete.py.zip' as the object key names.Upload the two Lambda function zip files from the 'Lambda_Code' folder of the cloned repository to your master account's Amazon S3 bucket. 
Note: These Lambda functions are used to create and delete AWS Backup resources in the target account.

```bash
aws s3 cp Lambda_Code/aws_backup_create.py.zip s3://your-s3-bucket/

aws s3 cp Lambda_Code/aws_backup_delete.py.zip s3://your-s3-bucket/
```

3.	Deploy the Master Account CloudFormation Template:
•	Deploy the 'masterAcct.yml' CloudFormation template from the 'CloudFormation_Templates' folder of the cloned repository in the AWS CloudFormation console of the master account. 
•	This template is for setting up AWS Lambda functions to create and delete backups, along with the necessary roles and permissions.

```bash
aws cloudformation create-stack --stack-name MasterAccountStack --template-body file://CloudFormation_Templates/masterAcct.yml
```

4.	Deploy the Target Account CloudFormation Template:

•	Deploy the 'targetAcct.yml' CloudFormation template from the 'CloudFormation_Templates' folder of the cloned repository in the AWS CloudFormation console of the target account's primary region (i.e us-east-1). 

```bash
aws cloudformation create-stack --stack-name TargetAccountStack --template-body file://CloudFormation_Templates/targetAcct.yml
```

This template creates below resources:

o	SSM Parameter Store parameter for an AWS Backup Plan, storing the backup plan configuration as a JSON object that can be referenced by AWS Backup to perform backups. 
o	Amazon RDS instance with the specified DB engine in a VPC.
o	IAM role required for the master account's Lambda functions to perform AWS Backup service deployment operations on the target account.
o	A custom role with specific AWS Backup policies used for performing backup operations in the target account.

5.	Create a KMS Multi-Region Key in the secondary region (us-east-2) region:
Deploy the KMSMultiRegionReplica.yml CloudFormation template in the target account’s us-east-2 region. Make sure you provide the KMSKeyArn id of the KMS alias ‘BackupBlogCredential’ Review the ‘user guide’ for more details on the deployment process.

```bash
aws cloudformation create-stack --stack-name KMSMultiRegionReplica --template-body file://CloudFormation_Templates/KMSMultiRegionReplica.yml
```

## Monitoring & Reporting
AWS Backup provides job status tracking and audit reports for compliance. Backup events can be monitored via AWS CloudWatch and SNS notifications.

## Cleanup Process
- Run the 'DeleteBackupLambda' function in the master account to remove backup resources.
- Verify that all recovery points are deleted (this may require multiple executions of the function).
- Delete CloudFormation stacks from both the master and target accounts to remove all associated resources.

## Conclusion
This solution simplifies AWS Backup management across multiple accounts, ensuring data protection, compliance, and automation. It can be extended to other AWS services beyond RDS by modifying backup selection criteria.
