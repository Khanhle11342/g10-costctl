import boto3
from botocore.exceptions import ClientError

from commands._common import confirm


def _terminate_ec2(rid, force):
    """Terminate one EC2 instance after confirmation."""

    if not confirm(f"Terminate EC2 {rid}?", force):
        print("Aborted.")
        return

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.terminate_instances(
        InstanceIds=[rid]
    )

    print(f"Terminated EC2 {rid}")


def _terminate_rds(rid, force):
    """Stop one RDS instance after confirmation."""

    if not confirm(f"Stop RDS {rid}?", force):
        print("Aborted.")
        return

    rds = boto3.client("rds", region_name="us-east-1")

    rds.stop_db_instance(
        DBInstanceIdentifier=rid
    )

    print(f"Stopped RDS {rid}")


def _terminate_s3(rid, force):
    """Delete one S3 bucket — refuse if it has any objects."""

    if not confirm(f"Delete S3 bucket {rid}?", force):
        print("Aborted.")
        return

    s3 = boto3.client("s3", region_name="us-east-1")

    response = s3.list_objects_v2(Bucket=rid)

    count = response.get("KeyCount", 0)

    if count > 0:
        print(
            f"Refusing — bucket {rid} has {count} object(s). Empty it first."
        )
        return

    s3.delete_bucket(Bucket=rid)

    print(f"Deleted S3 bucket {rid}")


def _terminate_volume(rid, force):
    """Delete one EBS volume after confirmation."""

    if not confirm(f"Delete volume {rid}?", force):
        print("Aborted.")
        return

    ec2 = boto3.client("ec2", region_name="us-east-1")

    ec2.delete_volume(
        VolumeId=rid
    )

    print(f"Deleted volume {rid}")


DISPATCH = {
    "ec2": _terminate_ec2,
    "rds": _terminate_rds,
    "s3": _terminate_s3,
    "volume": _terminate_volume,
}


def run(args):
    """Entry point."""

    try:

        DISPATCH[args.type](
            args.id,
            args.force
        )

    except ClientError as e:

        code = e.response["Error"]["Code"]
        message = e.response["Error"]["Message"]

        print(
            f"AWS error [{code}]: {message}"
        )