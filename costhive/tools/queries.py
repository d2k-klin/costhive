"""Bundled Steampipe / CloudQuery FinOps SQL.

Each query is authored to emit CostHive's stable column contract so the normalizer
is a direct field map (see costhive.normalize.parse_steampipe):

    title, description, category, service, region, resource,
    estimated_monthly_savings, confidence, recommended_action

Savings math is deliberately conservative and uses public on-demand list prices
baked in as constants — good enough to rank opportunities, and honest about
confidence. Prices drift; these are ballpark figures, hence confidence != high for
anything price-derived.
"""

from __future__ import annotations

# Rough public on-demand list prices (USD/month) used only to *rank* opportunities.
_EIP_UNATTACHED_MONTHLY = 3.60  # ~$0.005/hr for an idle Elastic IP
_EBS_GP3_PER_GB_MONTH = 0.08
_GP2_TO_GP3_SAVING_PER_GB = 0.016  # gp2 $0.10 -> gp3 $0.08 + baseline perf


#: name -> SQL. All read-only. Regions/accounts come from the Steampipe AWS plugin
#: connection, so no interpolation is needed here.
FINOPS_QUERIES: dict[str, str] = {
    "ebs_unattached": f"""
        select
          'Unattached EBS volume' as title,
          'Volume is in the "available" state (not attached to any instance) and still billing.' as description,
          'unused' as category,
          'ebs' as service,
          region,
          volume_id as resource,
          round((size * {_EBS_GP3_PER_GB_MONTH})::numeric, 2) as estimated_monthly_savings,
          'high' as confidence,
          'safe' as risk,
          'Snapshot then delete the volume, or reattach it if still needed.' as recommended_action,
          account_id
        from aws_ebs_volume
        where state = 'available'
    """,
    "eip_unassociated": f"""
        select
          'Unassociated Elastic IP' as title,
          'Elastic IP is allocated but not associated with a running resource, so it is billed hourly.' as description,
          'unused' as category,
          'ec2' as service,
          region,
          allocation_id as resource,
          {_EIP_UNATTACHED_MONTHLY} as estimated_monthly_savings,
          'high' as confidence,
          'safe' as risk,
          'Release the Elastic IP if it is no longer needed.' as recommended_action,
          account_id
        from aws_vpc_eip
        where association_id is null
    """,
    "ebs_gp2_to_gp3": f"""
        select
          'EBS gp2 volume can migrate to gp3' as title,
          'gp3 delivers baseline performance at ~20% lower per-GB cost than gp2.' as description,
          'storage_class' as category,
          'ebs' as service,
          region,
          volume_id as resource,
          round((size * {_GP2_TO_GP3_SAVING_PER_GB})::numeric, 2) as estimated_monthly_savings,
          'medium' as confidence,
          'moderate' as risk,
          'Modify the volume type from gp2 to gp3 (online, no downtime).' as recommended_action,
          account_id
        from aws_ebs_volume
        where volume_type = 'gp2'
    """,
    "stopped_instances_with_ebs": """
        select
          'Stopped instance still paying for EBS' as title,
          'Instance is stopped (no compute charge) but its attached EBS volumes still bill.' as description,
          'idle' as category,
          'ec2' as service,
          i.region,
          i.instance_id as resource,
          0 as estimated_monthly_savings,
          'medium' as confidence,
          'judgment' as risk,
          'If abandoned, terminate it and delete its volumes (confirm it is not a cold standby).' as recommended_action,
          i.account_id
        from aws_ec2_instance i
        where i.instance_state = 'stopped'
    """,
    "old_snapshots": """
        select
          'Old EBS snapshot' as title,
          'Snapshot is over a year old and may be retained beyond any backup policy.' as description,
          'unused' as category,
          'ebs' as service,
          region,
          snapshot_id as resource,
          round((volume_size * 0.05)::numeric, 2) as estimated_monthly_savings,
          'low' as confidence,
          'judgment' as risk,
          'Confirm it is outside retention/DR policy, then delete the snapshot.' as recommended_action,
          account_id
        from aws_ebs_snapshot
        where start_time < (now() - interval '365 days')
          and owner_id = account_id
    """,
}
