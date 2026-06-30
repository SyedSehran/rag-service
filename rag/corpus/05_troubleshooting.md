# Aster Cloud Storage — Troubleshooting

## "SignatureDoesNotMatch" errors

This almost always means the request was signed with an expired or rotated access key, or the system clock on the client is skewed by more than 15 minutes from UTC. Re-sync the client clock via NTP and confirm the key pair is still active in the console.

## Slow uploads

Large single-PUT uploads (over ~500 MB) are frequently bottlenecked by a single TCP connection. Switch to the multipart upload API and upload parts in parallel (4-8 concurrent parts is a good default) to use available bandwidth.

## 503 SlowDown errors

These indicate the per-prefix request-rate limit was exceeded. Spreading object keys across more distinct prefixes (instead of a single sequential prefix like a timestamp) lets Aster shard the prefix internally and raises the effective throughput ceiling.

## Objects not appearing in LIST results immediately

Aster is strongly consistent for new object writes as of the 2024 storage engine, so a PUT followed immediately by a LIST should reflect the new object. If an object is missing, check that the request went to the correct region endpoint — cross-region requests silently return an empty list rather than an error.
