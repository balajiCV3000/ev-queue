# AWS Cost Reduction Changes

> Context: low-traffic portfolio/showcase project running Flask on ECS Fargate (ap-south-1) behind an ALB.

---

## Change 1 — Remove the Application Load Balancer ✅ IMPLEMENTED

**What was changed in code**
- `Dockerfile`: Gunicorn now binds to port 80 (was 5000). `EXPOSE` updated to match.
- `.github/workflows/deploy.yml`:
  - Task definition jq now sets `portMappings` to port 80.
  - `update-service` passes `assignPublicIp=ENABLED` so the task gets a direct public IP.
  - New step retrieves the task's public IP via the ENI after deployment.
  - New step UPSERTs a Route 53 A record pointing your domain to the new IP (TTL 60s).

**One-time manual migration steps (do these once, in order)**

1. **Register or choose a domain** — Route 53 → Registered domains, or use a subdomain of a domain you already own. This will be your permanent public URL.

2. **Create a Route 53 Hosted Zone** (if you don't have one) — Route 53 → Hosted zones → Create. Note the Hosted Zone ID (format: `Z1234ABCDEF`).

3. **Add 4 GitHub Secrets** to your repo (Settings → Secrets → Actions):
   | Secret | Value |
   |---|---|
   | `ROUTE53_HOSTED_ZONE_ID` | Your hosted zone ID, e.g. `Z1234ABCDEF` |
   | `ROUTE53_DOMAIN` | Your domain, e.g. `ev-queue.yourdomain.com` |
   | `ECS_PUBLIC_SUBNET_IDS` | Comma-separated public subnet IDs, e.g. `subnet-abc,subnet-def` |
   | `ECS_SECURITY_GROUP_ID` | Security group ID that allows inbound TCP 80, e.g. `sg-abc123` |

4. **Update the security group** — In EC2 → Security Groups, find the SG attached to your ECS tasks. Add an inbound rule: Type `HTTP`, Port `80`, Source `0.0.0.0/0`.

5. **Recreate the ECS service without the ALB** — ECS does not allow removing a load balancer from an existing service. Run these CLI commands once:
   ```bash
   # Scale down and delete old service (ALB-linked)
   aws ecs update-service --cluster ev-queue-3-cluster --service ev-queue-3-service --desired-count 0 --region ap-south-1
   aws ecs delete-service --cluster ev-queue-3-cluster --service ev-queue-3-service --force --region ap-south-1

   # Create new service without load balancer
   # Replace <TASK_DEF_ARN>, <SUBNET_IDS>, <SG_ID> with your values
   aws ecs create-service \
     --cluster ev-queue-3-cluster \
     --service-name ev-queue-3-service \
     --task-definition <TASK_DEF_ARN> \
     --desired-count 1 \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_IDS>],securityGroups=[<SG_ID>],assignPublicIp=ENABLED}" \
     --region ap-south-1
   ```

6. **Delete the ALB and target group** — EC2 → Load Balancers → delete `ev-queue-3-*`. EC2 → Target Groups → delete the associated target group.

7. **Add Route 53 health check** (replaces ALB health checks) — Route 53 → Health checks → Create:
   - Protocol: `HTTP`
   - Domain name: your domain (e.g. `ev-queue.yourdomain.com`)
   - Port: `80`
   - Path: `/health`
   - Request interval: `30 seconds`
   - Failure threshold: `3`

8. **Update IAM permissions** — The GitHub Actions IAM user needs two new permissions:
   - `route53:ChangeResourceRecordSets` on the hosted zone resource
   - `ec2:DescribeNetworkInterfaces` on `*`

9. **Update all existing links** — this is the one and only time your URL changes. Replace the old ALB hostname with your new domain everywhere you've shared it.

10. **Push to master** — the deploy workflow now handles all future deployments automatically. The domain stays permanent; only the IP it points to changes behind the scenes.

**Impact on project**
- The public link is stable forever — the domain never changes, only what IP it resolves to.
- No ALB health checks; replaced by Route 53 health check monitoring the `/health` endpoint.
- Flask/Gunicorn unchanged; only the bind port moved from 5000 to 80.

**Cost reduction**
ALB fixed base charge ~$16–18/month eliminated entirely. Route 53 hosted zone: $0.50/month. Route 53 health check: $0.50/month. Net saving: **~$15–17/month**.

---

## Change 2 — Move ECS Tasks to a Public Subnet and Remove the NAT Gateway

**What to do**
In your VPC, move the ECS service to a public subnet. Set `assignPublicIp: ENABLED` on the task (needed to pull images from ECR without a NAT). Delete the NAT Gateway and its associated Elastic IP.

**Impact on project**
- ECS tasks will have a direct public IP for outbound traffic (ECR pulls, Google Maps API calls). This is safe for a single-container app with no sensitive internal services to protect.
- If you have any other private resources in the VPC (RDS, ElastiCache), they would lose NAT-based outbound access — not applicable here since the app has no database.
- No application code changes required.

**Cost reduction**
NAT Gateway charges: $0.045/hr (~$32/month) + $0.045/GB data processing. For a showcase app this is almost entirely waste. Removing it saves $20–35/month depending on how much outbound data flows through it.

---

## Change 3 — Switch to Fargate Spot Capacity Provider

**What to do**
In the ECS service definition, change the capacity provider strategy from `FARGATE` to `FARGATE_SPOT`. Update the service via the AWS console or CLI:

```bash
aws ecs update-service \
  --cluster ev-queue-3-cluster \
  --service ev-queue-3-service \
  --capacity-provider-strategy '[{"capacityProvider":"FARGATE_SPOT","weight":1}]'
```

**Impact on project**
- Spot tasks can be interrupted by AWS (rare, but possible). The task will restart automatically within a minute or two. For a demo app this is an acceptable trade-off.
- In-memory simulation state will be lost on an interruption, same as a normal restart. No data persistence is affected since none exists today.
- No code or Dockerfile changes required.

**Cost reduction**
Fargate Spot is 50–70% cheaper than standard Fargate. At the minimum task size (0.25 vCPU / 0.5 GB), standard cost is ~$8–9/month. Spot brings this to ~$2.50–4/month.

---

## Change 4 — Right-Size the Fargate Task to Minimum

**What to do**
In the ECS task definition, set:
- `cpu: 256` (0.25 vCPU)
- `memory: 512` (0.5 GB)

Register a new task definition revision and update the service to use it. Verify the app starts cleanly — Flask + Gunicorn + the simulation engine comfortably fit in 512 MB.

**Impact on project**
- No functional change. The simulation is single-threaded and CPU-light between ticks.
- If you notice sluggish simulation under load, bumping to `cpu: 512` (0.5 vCPU) is the next step up.

**Cost reduction**
If currently running at 0.5 vCPU / 1 GB or higher, dropping to 0.25 vCPU / 0.5 GB halves the compute cost. Savings: ~$4–5/month on top of Spot pricing.

---

## Change 5 — Scale to Zero When Not in Use

**What to do**
When the app is not being actively demonstrated, set desired task count to 0:

```bash
aws ecs update-service \
  --cluster ev-queue-3-cluster \
  --service ev-queue-3-service \
  --desired-count 0
```

Scale back up to 1 before a demo:

```bash
aws ecs update-service \
  --cluster ev-queue-3-cluster \
  --service ev-queue-3-service \
  --desired-count 1
```

Optionally add a `scale-down` and `scale-up` step to the deploy workflow, or schedule it with EventBridge if there is a predictable usage window.

**Impact on project**
- The app will be unreachable while scaled to zero. There is no warm-up time concern beyond the ~30–60 second ECS task startup.
- Simulation state resets on every scale-up regardless, so no additional state loss.

**Cost reduction**
Fargate charges only for running tasks. At 0 desired count, compute cost is $0. If the app runs 5 days/month for demos, cost drops from ~$3–4/month (Spot) to ~$0.50/month.

---

## Change 6 — Add an ECR Lifecycle Policy

**What to do**
In ECR → `ev-queue-3` repository → Lifecycle policy, add a rule to expire images older than 7 days or keep only the 5 most recent:

```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep last 5 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 5
      },
      "action": { "type": "expire" }
    }
  ]
}
```

**Impact on project**
- Old unused images are deleted automatically. The deploy workflow always pushes a fresh SHA-tagged image, so this only removes stale history.
- Rollback to an image older than the 5 most recent would require a rebuild. For a showcase app this is not a concern.

**Cost reduction**
ECR storage is $0.10/GB/month. Each image is roughly 150–300 MB. Without a lifecycle policy, months of deployments accumulate silently. Savings are small (cents) but storage grows unbounded over time.

---

## Summary

| # | Change | Est. Savings/month | Project Impact |
|---|---|---|---|
| 1 | Remove ALB | ~$16–18 | Requires DNS update on deploy; no app changes |
| 2 | Remove NAT Gateway | ~$20–35 | Move to public subnet; no app changes |
| 3 | Fargate Spot | ~$4–6 | Rare restarts possible; acceptable for demos |
| 4 | Right-size task (0.25 vCPU / 512 MB) | ~$4–5 | No functional change |
| 5 | Scale to zero when idle | ~$2–3 | App offline between demos |
| 6 | ECR lifecycle policy | <$1 | Old images auto-deleted |

**Combined potential savings: ~$46–68/month → under $1–2/month** (running only during active demos on Spot with no ALB or NAT Gateway).
