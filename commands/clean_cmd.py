"""clean — (stretch) bulk terminate resources matching a tag."""

import boto3

from commands._common import parse_kv, tags_to_dict


def _find_targets(tag_key, tag_val):
    """Return {"ec2": [...], "volume": [...]} matching tag in non-terminal state."""

    ec2 = boto3.client("ec2", region_name="us-east-1")

    targets = {
        "ec2": [],
        "volume": [],
    }

    # EC2 instances
    response = ec2.describe_instances()

    for reservation in response["Reservations"]:

        for instance in reservation["Instances"]:

            state = instance["State"]["Name"]

            # skip already terminated
            if state in ["terminated", "shutting-down"]:
                continue

            tags = tags_to_dict(
                instance.get("Tags", [])
            )

            if tags.get(tag_key) == tag_val:

                targets["ec2"].append(
                    instance["InstanceId"]
                )

    # volumes
    response = ec2.describe_volumes()

    for volume in response["Volumes"]:

        # only available volumes
        if volume["State"] != "available":
            continue

        tags = tags_to_dict(
            volume.get("Tags", [])
        )

        if tags.get(tag_key) == tag_val:

            targets["volume"].append(
                volume["VolumeId"]
            )

    return targets


def run(args):
    """Entry point."""

    tag_key, tag_val = parse_kv(args.tag)

    targets = _find_targets(
        tag_key,
        tag_val,
    )

    ec2_count = len(targets["ec2"])
    volume_count = len(targets["volume"])

    total = ec2_count + volume_count

    if total == 0:

        print("Nothing to clean")
        return

    print(
        f"Found {ec2_count} EC2 and {volume_count} volume(s)"
    )

    # dry run
    if not args.apply:

        for iid in targets["ec2"]:
            print(f"Would terminate EC2 {iid}")

        for vid in targets["volume"]:
            print(f"Would delete volume {vid}")

        print("(dry-run — pass --apply to execute)")

        return

    ec2 = boto3.client(
        "ec2",
        region_name="us-east-1"
    )

    # terminate instances
    if targets["ec2"]:

        ec2.terminate_instances(
            InstanceIds=targets["ec2"]
        )

        for iid in targets["ec2"]:
            print(f"Terminated EC2 {iid}")

    # delete volumes
    for vid in targets["volume"]:

        ec2.delete_volume(
            VolumeId=vid
        )

        print(f"Deleted volume {vid}")