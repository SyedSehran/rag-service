# Aster Cloud Storage — Product Overview

Aster Cloud Storage is an object storage service for storing and retrieving files of any size. It exposes an S3-compatible API and a web console.

## Core Concepts

A **bucket** is the top-level container for objects. Bucket names must be globally unique within an account and are limited to 3-63 characters. Objects are stored as key-value pairs inside a bucket, where the key is the full path string.

Every object has metadata attached: content type, size, checksum, and up to 10 custom key-value tags. Tags are searchable through the metadata filter API.

## Storage Classes

Aster offers three storage classes:

- **Standard** — for frequently accessed data, lowest latency, highest per-GB price.
- **Infrequent Access (IA)** — for data accessed less than once a month, ~45% cheaper per GB than Standard, with a retrieval fee.
- **Archive** — for long-term retention, cheapest per-GB price, retrieval takes 3-5 hours.

Objects can be transitioned between classes automatically using lifecycle rules.

## Regions

Aster is available in four regions: us-east, us-west, eu-central, and ap-south. Cross-region replication is supported but billed separately for egress.
