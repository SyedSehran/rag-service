# Aster Cloud Storage — Security & Access Control

## Authentication

Every API request must be signed using an access key pair (access key ID + secret access key). Aster supports the same signing process (SigV4-style) as most S3-compatible tooling. Keys can be rotated from the console at any time; old keys remain valid for 24 hours after rotation to avoid downtime.

## Encryption

All objects are encrypted at rest using AES-256 by default; no configuration is required. Customers may optionally bring their own encryption key (BYOK) for an additional $0.002 per GB-month managed-key fee. Data in transit is encrypted via TLS 1.2 or higher; plaintext HTTP requests are rejected.

## Bucket Policies

Access to a bucket is controlled by a JSON policy attached to the bucket, plus optional per-object ACLs. Policies can restrict access by IP range, by VPC endpoint, or by requiring a specific request header. Public buckets are blocked by default and must be explicitly enabled with a console confirmation step.

## Audit Logging

All API calls can be logged to a separate audit bucket, including the caller identity, source IP, action, and response code. Audit logs are retained for 90 days by default and can be exported to a SIEM via webhook.
