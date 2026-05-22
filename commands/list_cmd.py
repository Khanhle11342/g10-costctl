import boto3
from botocore.exceptions import ClientError

from commands._common import parse_kv, tags_to_dict, tags_match


def _list_ec2(want, missing):
    """List EC2 instances matching tag filters."""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    rows = []

    paginator = ec2.get_paginator("describe_instances")

    for page in paginator.paginate():

        for reservation in page["Reservations"]:

            for instance in reservation["Instances"]:

                tags = tags_to_dict(instance.get("Tags", []))

                if not tags_match(tags, want, missing):
                    continue

                rows.append(
                    (
                        instance["InstanceId"],
                        instance["InstanceType"],
                        instance["State"]["Name"],
                        tags,
                    )
                )

    return rows


def _list_rds(want, missing):
    """Same shape as _list_ec2 but for RDS DB instances."""

    rds = boto3.client("rds", region_name="us-east-1")

    rows = []

    response = rds.describe_db_instances()

    for db in response["DBInstances"]:

        tag_response = rds.list_tags_for_resource(
            ResourceName=db["DBInstanceArn"]
        )

        tags = tags_to_dict(tag_response.get("TagList", []))

        if not tags_match(tags, want, missing):
            continue

        rows.append(
            (
                db["DBInstanceIdentifier"],
                db["DBInstanceClass"],
                db["DBInstanceStatus"],
                tags,
            )
        )

    return rows


def _list_s3(want, missing):
    """List S3 buckets matching tag filters."""

    s3 = boto3.client("s3", region_name="us-east-1")

    rows = []

    response = s3.list_buckets()

    for bucket in response["Buckets"]:

        name = bucket["Name"]

        try:

            tag_response = s3.get_bucket_tagging(Bucket=name)

            tags = tags_to_dict(tag_response.get("TagSet", []))

        except ClientError:
            tags = {}

        if not tags_match(tags, want, missing):
            continue

        rows.append(
            (
                name,
                "bucket",
                "active",
                tags,
            )
        )

    return rows


def _list_volume(want, missing):
    """List EBS volumes matching tag filters."""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    rows = []

    paginator = ec2.get_paginator("describe_volumes")

    for page in paginator.paginate():

        for volume in page["Volumes"]:

            tags = tags_to_dict(volume.get("Tags", []))

            if not tags_match(tags, want, missing):
                continue

            rows.append(
                (
                    volume["VolumeId"],
                    f'{volume["VolumeType"]}-{volume["Size"]}GB',
                    volume["State"],
                    tags,
                )
            )

    return rows


DISPATCH = {
    "ec2": _list_ec2,
    "rds": _list_rds,
    "s3": _list_s3,
    "volume": _list_volume,
}


def run(args):
    """Entry point called by costctl.py."""

    want = [parse_kv(x) for x in args.tag]
    missing = args.missing_tag

    rows = DISPATCH[args.type](want, missing)

    print(f"{args.type.upper()} — {len(rows)} found:")
    print("-" * 78)

    for rid, rtype, state, tags in rows:

        tag_str = " ".join(
            [f"{k}={v}" for k, v in tags.items()]
        )

        print(
            f"{rid:<25} {rtype:<15} {state:<12} {tag_str}"
        )