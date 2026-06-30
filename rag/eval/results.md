# Evaluation Results

k=5, n=8 questions, embed_model=hashing-tfidf-offline-v1 (dim=384)

## Retrieval

- recall_at_k_hit_rate: 0.714
- mrr: 0.512
- ndcg_at_k: 0.562
- context_precision: 0.143

## Answer

- faithfulness_mean: 1.000
- relevance_mean: 0.134
- em_mean: 0.000
- f1_mean: 0.064
- no_context_handling_accuracy: 0.000

## Latency (ms)

- p50: 0.664
- p95: 2.164
- mean: 0.805

## Per-query detail

### q1: What encryption algorithm does Aster use for objects at rest by default?
- hit=1.0 rr=1.0 ndcg=1.0 ctx_precision=0.2
- faithfulness=1.0 relevance=0.15384615384615385 em=0.0 f1=0.031746031746031744
- grounded=True latency_ms=2.164 tokens=1261
- answer: ## Encryption All objects are encrypted at rest using AES-256 by default; no configuration is required. [03_security.md#0] ## Objects not appearing in LIST results immediately Aster is strongly consistent for new object writes as of the 2024 storage engine, so a PUT followed immediately by a LIST should reflect the new object. [05_troubleshooting.md#0] ## Core Concepts A **bucket** is the top-level container for objects. [01_overview.md#0]

### q2: How much does Infrequent Access storage cost per GB per month?
- hit=1.0 rr=1.0 ndcg=1.0 ctx_precision=0.2
- faithfulness=1.0 relevance=0.1346153846153846 em=0.0 f1=0.125
- grounded=True latency_ms=0.9 tokens=1300
- answer: # Aster Cloud Storage — Pricing ## Storage Pricing (per GB / month) | Storage class | Price | |---|---| | Standard | $0.023 | | Infrequent Access | $0.0125 | | Archive | $0.0036 | ## Request Pricing PUT, COPY, POST, LIST requests cost $0.005 per 1,000 requests. [02_pricing.md#0] - **Infrequent Access (IA)** — for data accessed less than once a month, ~45% cheaper per GB than Standard, with a retrieval fee. [01_overview.md#0] ## Storage Classes Aster offers three storage classes: - **Standard** — for frequently accessed data, lowest latency, highest per-GB price. [01_overview.md#0]

### q3: What is the maximum number of parts allowed in a multipart upload?
- hit=1.0 rr=0.3333333333333333 ndcg=0.5 ctx_precision=0.2
- faithfulness=1.0 relevance=0.17647058823529413 em=0.0 f1=0.03076923076923077
- grounded=True latency_ms=0.664 tokens=1095
- answer: Switch to the multipart upload API and upload parts in parallel (4-8 concurrent parts is a good default) to use available bandwidth. [05_troubleshooting.md#0] Maximum single-request upload size is 5 GB. [04_api_reference.md#0] in LIST results immediately Aster is strongly consistent for new object writes as of the 2024 storage engine, so a PUT followed immediately by a LIST should reflect the new object. [05_troubleshooting.md#1]

### q4: What should I check if I get a SignatureDoesNotMatch error?
- hit=1.0 rr=0.25 ndcg=0.43067655807339306 ctx_precision=0.2
- faithfulness=1.0 relevance=0.17647058823529413 em=0.0 f1=0.0784313725490196
- grounded=True latency_ms=0.495 tokens=939
- answer: Exceeding the limit returns a 503 SlowDown error; clients should retry with exponential backoff. [04_api_reference.md#0] If an object is missing, check that the request [05_troubleshooting.md#0] ## Listing Objects `GET /{bucket}?prefix=&max-keys=` lists objects in a bucket. [04_api_reference.md#0]

### q5: How many storage classes does Aster offer and what are they?
- hit=0.0 rr=0.0 ndcg=0.0 ctx_precision=0.0
- faithfulness=1.0 relevance=0.10416666666666667 em=0.0 f1=0.09999999999999999
- grounded=True latency_ms=0.501 tokens=1094
- answer: ## Storage Classes Aster offers three storage classes: - **Standard** — for frequently accessed data, lowest latency, highest per-GB price. [01_overview.md#0] # Aster Cloud Storage — Product Overview Aster Cloud Storage is an object storage service for storing and retrieving files of any size. [01_overview.md#0] ## Billing Cycle Bills are calculated daily and invoiced monthly in arrears. [02_pricing.md#0]

### q6: What is the per-bucket PUT request rate limit?
- hit=0.0 rr=0.0 ndcg=0.0 ctx_precision=0.0
- faithfulness=1.0 relevance=0.10256410256410256 em=0.0 f1=0.0
- grounded=True latency_ms=0.776 tokens=1066
- answer: ## 503 SlowDown errors These indicate the per-prefix request-rate limit was exceeded. [05_troubleshooting.md#0] If an object is missing, check that the request [05_troubleshooting.md#0] ## Bucket Policies Access to a bucket is controlled by a JSON policy attached to the bucket, plus optional per-object ACLs. [03_security.md#0]

### q7: How long are old access keys valid after rotation?
- hit=1.0 rr=1.0 ndcg=1.0 ctx_precision=0.2
- faithfulness=1.0 relevance=0.13953488372093023 em=0.0 f1=0.0851063829787234
- grounded=True latency_ms=0.449 tokens=958
- answer: Keys can be rotated from the console at any time; old keys remain valid for 24 hours after rotation to avoid downtime. [03_security.md#0] Tags are searchable through the metadata filter API. [01_overview.md#0] - **Archive** — for long-term retention, cheapest per-GB price, retrieval takes 3-5 hours. [01_overview.md#0]

### q8: What is the capital of France?
- hit=None rr=None ndcg=None ctx_precision=None
- faithfulness=1.0 relevance=0.08333333333333333 em=None f1=None
- grounded=True latency_ms=0.489 tokens=888
- answer: ## Data Transfer The first 100 GB of data transferred out to the internet each month is free. [02_pricing.md#0] If an object is missing, check that the request [05_troubleshooting.md#0] ## Core Concepts A **bucket** is the top-level container for objects. [01_overview.md#0]

