"""Static cost model: self-hosted FAISS-on-a-small-VM vs a managed,
pod-based vector DB, at 100K / 1M / 10M vectors. All assumptions are
parameters at the top of the file so the numbers are auditable and
re-runnable, not hardcoded into prose.

Usage: python -m eval.cost_comparison
"""

DIM = 384
BYTES_PER_FLOAT = 4
VECTOR_BYTES = DIM * BYTES_PER_FLOAT  # flat index, no compression
OVERHEAD_FACTOR = 1.3  # metadata + sqlite + faiss internal overhead, rounded up

# Self-hosted: a single small VM running FAISS in-process + SQLite, sized
# to keep the whole index in RAM. Pricing approximates a generic cloud
# provider's general-purpose VM tier (e.g. AWS t3/m6i, GCP e2) as of 2025.
VM_TIERS = [
    # (max_GB_ram, $/month)
    (2, 12),
    (4, 24),
    (8, 48),
    (16, 96),
    (32, 192),
    (64, 384),
]
STORAGE_DISK_PER_GB_MONTH = 0.10  # SSD-backed persistent disk, for the .faiss + .sqlite files

# Managed vector DB: pod-based pricing model (e.g. Pinecone-style),
# where pods are provisioned for peak capacity and billed whether or not
# they're queried -- this is the core cost driver this assignment asks us
# to interrogate. One "p1" pod ~ holds up to ~1M vectors of this
# dimensionality comfortably, at ~$70/month per pod (approximate public
# list price order of magnitude as of 2025; treat as illustrative).
MANAGED_POD_CAPACITY = 1_000_000
MANAGED_POD_PRICE = 70


def self_hosted_cost(n_vectors: int) -> float:
    needed_gb = (n_vectors * VECTOR_BYTES * OVERHEAD_FACTOR) / (1024 ** 3)
    vm_cost = None
    for max_gb, price in VM_TIERS:
        if needed_gb <= max_gb * 0.7:  # leave headroom, don't run a VM at 100% RAM
            vm_cost = price
            break
    if vm_cost is None:
        vm_cost = VM_TIERS[-1][1] * (needed_gb / (VM_TIERS[-1][0] * 0.7))
    disk_cost = needed_gb * STORAGE_DISK_PER_GB_MONTH
    return round(vm_cost + disk_cost, 2)


def managed_cost(n_vectors: int) -> float:
    pods_needed = max(1, -(-n_vectors // MANAGED_POD_CAPACITY))  # ceil div
    return round(pods_needed * MANAGED_POD_PRICE, 2)


if __name__ == "__main__":
    print(f"{'Vectors':>10} | {'Self-hosted ($/mo)':>20} | {'Managed ($/mo)':>16} | Savings")
    for n in [100_000, 1_000_000, 10_000_000]:
        sh = self_hosted_cost(n)
        mg = managed_cost(n)
        savings_pct = round((1 - sh / mg) * 100, 1) if mg else None
        print(f"{n:>10,} | {sh:>20,.2f} | {mg:>16,.2f} | {savings_pct}%")
