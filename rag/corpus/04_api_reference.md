# Aster Cloud Storage — API Reference (excerpt)

## Uploading an Object

`PUT /{bucket}/{key}` uploads an object. Maximum single-request upload size is 5 GB. For larger files, use the multipart upload API, which splits the object into parts of at least 5 MB each (except the final part) and supports up to 10,000 parts per object.

## Listing Objects

`GET /{bucket}?prefix=&max-keys=` lists objects in a bucket. Results are paginated with a continuation token; max-keys defaults to 1,000 and cannot exceed 1,000 per page.

## Deleting Objects

`DELETE /{bucket}/{key}` deletes a single object. `POST /{bucket}?delete` accepts a batch delete request body listing up to 1,000 keys in one call.

## Rate Limits

Each bucket supports up to 3,500 PUT/POST/DELETE requests per second and 5,500 GET requests per second per prefix. Exceeding the limit returns a 503 SlowDown error; clients should retry with exponential backoff.

## Error Codes

Common error codes include 403 (signature invalid or access denied), 404 (no such key or bucket), 409 (bucket already exists, on creation), and 503 (rate limited or temporary unavailability).
