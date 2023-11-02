import boto3
import csv
import os
from datetime import datetime, timedelta

Buckets3name = os.environ['Buckets3name']

print(Buckets3name)

def is_snapshot_used_by_ami(snapshot_id):
    ec2 = boto3.client('ec2')
    response = ec2.describe_images(Filters=[{'Name': 'block-device-mapping.snapshot-id', 'Values': [snapshot_id]}])
    return len(response['Images']) > 0

def delete_snapshot(snapshot_id):
    # Function to delete a single snapshot by ID
    ec2 = boto3.client('ec2')
    ec2.delete_snapshot(SnapshotId=snapshot_id)

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    response = ec2.describe_snapshots(OwnerIds=['self'])
    snapshots = response['Snapshots']

    with open('/tmp/snapshot_report.csv', 'w', newline='') as csvfile:
        fieldnames = ['Snapshot ID', 'Start Time', 'Age (Days)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for snapshot in snapshots:
            snapshot_id = snapshot['SnapshotId']
            start_time = snapshot['StartTime']
            snapshot_age = datetime.now(start_time.tzinfo) - start_time
            if snapshot_age.days > 90 and not is_snapshot_used_by_ami(snapshot_id):
                writer.writerow({'Snapshot ID': snapshot_id, 'Start Time': start_time, 'Age (Days)': snapshot_age.days})
                # Delete the snapshot
                delete_snapshot(snapshot_id)

    s3 = boto3.resource('s3')
    s3.meta.client.upload_file('/tmp/snapshot_report.csv', 'Buckets3name', 'snapshot_report.csv')